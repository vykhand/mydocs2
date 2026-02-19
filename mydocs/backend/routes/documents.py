"""Document endpoint handlers."""

import os
import re
from typing import Optional

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response

from mydocs.backend.dependencies import (
    BatchParseRequest,
    BatchParseResponse,
    DocumentListResponse,
    IngestRequest,
    IngestResponse,
    ParseRequest,
    ParseResponse,
    TagsRequest,
)
from mydocs.parsing.base_parser import DocumentLockedException
from mydocs.models import Document, DocumentPage, StorageBackendEnum, StorageModeEnum
from mydocs.parsing.pipeline import batch_parse, ingest_files, parse_document
from mydocs.parsing.storage import get_storage
import mydocs.config as C

router = APIRouter(prefix="/api/v1/documents")


def _error(status_code: int, error_code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "error_code": error_code, "status_code": status_code},
    )


MIME_MAP = {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
}


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="ISO date string (inclusive)"),
    date_to: Optional[str] = Query(None, description="ISO date string (inclusive)"),
):
    query = {}
    if status:
        query["status"] = status
    if file_type:
        query["file_type"] = file_type
    if document_type:
        query["document_type"] = document_type
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            query["tags"] = {"$all": tag_list}
    if search:
        query["original_file_name"] = {"$regex": re.escape(search), "$options": "i"}
    if date_from or date_to:
        date_filter = {}
        if date_from:
            date_filter["$gte"] = date_from
        if date_to:
            date_filter["$lte"] = date_to + "T23:59:59"
        query["created_at"] = date_filter

    sort_dir = -1 if sort_order == "desc" else 1
    skip = (page - 1) * page_size

    total = await Document.acount(query)
    docs = await Document.afind(
        query,
        sort=[(sort_by, sort_dir)],
        skip=skip,
        limit=page_size,
    )

    return DocumentListResponse(
        documents=[d.model_dump(by_alias=False, exclude_none=True) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/upload", response_model=IngestResponse)
async def upload_files(
    files: list[UploadFile] = File(...),
    tags: str = Form(""),
    parse_after_upload: bool = Form(False),
):
    upload_dir = os.path.join(C.DATA_FOLDER, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    saved_paths = []
    for f in files:
        dest = os.path.join(upload_dir, f.filename)
        content = await f.read()
        with open(dest, "wb") as out:
            out.write(content)
        saved_paths.append(dest)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    documents, skipped = await ingest_files(
        source=saved_paths,
        storage_mode=StorageModeEnum.MANAGED,
        tags=tag_list,
    )

    if parse_after_upload:
        doc_ids = [doc.id for doc in documents]
        if doc_ids:
            await batch_parse(document_ids=doc_ids)

    return IngestResponse(
        documents=[
            {"id": doc.id, "file_name": doc.file_name, "status": doc.status}
            for doc in documents
        ],
        skipped=skipped,
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    documents, skipped = await ingest_files(
        source=request.source,
        storage_mode=request.storage_mode,
        tags=request.tags,
        recursive=request.recursive,
        storage_backend=request.storage_backend,
    )
    return IngestResponse(
        documents=[
            {"id": doc.id, "file_name": doc.file_name, "status": doc.status}
            for doc in documents
        ],
        skipped=skipped,
    )


@router.post("/parse", response_model=BatchParseResponse)
async def parse_batch(request: BatchParseRequest):
    queued, skipped = await batch_parse(
        document_ids=request.document_ids,
        tags=request.tags,
        status_filter=request.status_filter,
    )
    return BatchParseResponse(queued=queued, skipped=skipped)


@router.post("/{document_id}/parse", response_model=ParseResponse)
async def parse_single(document_id: str, request: ParseRequest | None = None):
    config_override = request.parser_config_override if request else None
    try:
        doc = await parse_document(document_id, parser_config_override=config_override)
    except ValueError:
        return _error(404, "DOCUMENT_NOT_FOUND", f"Document {document_id} not found")
    except DocumentLockedException:
        return _error(409, "DOCUMENT_LOCKED", f"Document {document_id} is currently being parsed")

    return ParseResponse(
        document_id=doc.id,
        status=doc.status,
        page_count=doc.file_metadata.page_count if doc.file_metadata and doc.file_metadata.page_count else 0,
        element_count=len(doc.elements) if doc.elements else 0,
    )


@router.get("/{document_id}")
async def get_document(document_id: str):
    doc = await Document.aget(document_id)
    if not doc:
        return _error(404, "DOCUMENT_NOT_FOUND", f"Document {document_id} not found")
    return doc.model_dump(by_alias=False, exclude_none=True)


@router.get("/{document_id}/file")
async def get_document_file(document_id: str):
    doc = await Document.aget(document_id)
    if not doc:
        return _error(404, "DOCUMENT_NOT_FOUND", f"Document {document_id} not found")

    file_path = doc.managed_path or doc.original_path

    # Azure Blob: redirect to SAS URL
    if doc.storage_backend == StorageBackendEnum.AZURE_BLOB and file_path:
        storage = get_storage(StorageBackendEnum.AZURE_BLOB)
        sas_url = await storage.generate_download_url(file_path)
        if sas_url:
            return RedirectResponse(url=sas_url, status_code=307)
        return _error(500, "SAS_GENERATION_FAILED", "Failed to generate download URL")

    # Local: serve file directly
    if not file_path or not os.path.isfile(file_path):
        return _error(404, "FILE_NOT_FOUND", f"File not found for document {document_id}")

    media_type = MIME_MAP.get(doc.file_type, "application/octet-stream")
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=doc.original_file_name,
    )


@router.get("/{document_id}/pages")
async def get_pages(document_id: str):
    doc = await Document.aget(document_id)
    if not doc:
        return _error(404, "DOCUMENT_NOT_FOUND", f"Document {document_id} not found")
    pages = await DocumentPage.afind({"document_id": document_id})
    return [p.model_dump(by_alias=False, exclude_none=True) for p in pages]


@router.get("/{document_id}/pages/{page_number}")
async def get_page(document_id: str, page_number: int):
    page = await DocumentPage.afind_one(
        {"document_id": document_id, "page_number": page_number}
    )
    if not page:
        return _error(404, "DOCUMENT_NOT_FOUND", f"Page {page_number} not found for document {document_id}")
    return page.model_dump(by_alias=False, exclude_none=True)


@router.post("/{document_id}/tags")
async def add_tags(document_id: str, request: TagsRequest):
    doc = await Document.aget(document_id)
    if not doc:
        return _error(404, "DOCUMENT_NOT_FOUND", f"Document {document_id} not found")
    await Document.aupdate_one(
        {"_id": document_id},
        {"$addToSet": {"tags": {"$each": request.tags}}},
    )
    updated = await Document.aget(document_id)
    return updated.model_dump(by_alias=False, exclude_none=True)


@router.delete("/{document_id}/tags/{tag}")
async def remove_tag(document_id: str, tag: str):
    doc = await Document.aget(document_id)
    if not doc:
        return _error(404, "DOCUMENT_NOT_FOUND", f"Document {document_id} not found")
    await Document.aupdate_one(
        {"_id": document_id},
        {"$pull": {"tags": tag}},
    )
    updated = await Document.aget(document_id)
    return updated.model_dump(by_alias=False, exclude_none=True)


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    doc = await Document.aget(document_id)
    if not doc:
        return _error(404, "DOCUMENT_NOT_FOUND", f"Document {document_id} not found")

    # Delete pages
    await DocumentPage.adelete_many({"document_id": document_id})

    # Delete managed file and sidecar via storage backend
    if doc.managed_path:
        storage = get_storage(doc.storage_backend)
        try:
            await storage.delete_file(doc.managed_path)
        except Exception:
            pass  # Best-effort deletion
        # Delete managed sidecar
        try:
            if doc.storage_backend == StorageBackendEnum.AZURE_BLOB:
                from mydocs.parsing.storage.azure_blob import make_az_uri, parse_az_uri
                container, _ = parse_az_uri(doc.managed_path)
                sidecar_blob = make_az_uri(container, f"{doc.id}.metadata.json")
                await storage.delete_file(sidecar_blob)
            else:
                sidecar_path = os.path.join(os.path.dirname(doc.managed_path), f"{doc.id}.metadata.json")
                await storage.delete_file(sidecar_path)
        except Exception:
            pass  # Best-effort sidecar deletion

    # Delete sidecar metadata file for external mode (never delete the original file)
    if doc.storage_mode == StorageModeEnum.EXTERNAL and doc.original_path:
        sidecar = os.path.join(
            os.path.dirname(doc.original_path), f"{doc.id}.metadata.json"
        )
        if os.path.isfile(sidecar):
            os.remove(sidecar)

    # Delete document
    await Document.adelete_one({"_id": document_id})

    return Response(status_code=204)
