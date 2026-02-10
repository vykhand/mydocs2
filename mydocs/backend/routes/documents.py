"""Document endpoint handlers."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from mydocs.backend.dependencies import (
    BatchParseRequest,
    BatchParseResponse,
    IngestRequest,
    IngestResponse,
    ParseRequest,
    ParseResponse,
    TagsRequest,
)
from mydocs.parsing.base_parser import DocumentLockedException
from mydocs.parsing.models import Document, DocumentPage
from mydocs.parsing.pipeline import batch_parse, ingest_files, parse_document

router = APIRouter(prefix="/api/v1/documents")


def _error(status_code: int, error_code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "error_code": error_code, "status_code": status_code},
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    documents, skipped = await ingest_files(
        source=request.source,
        storage_mode=request.storage_mode,
        tags=request.tags,
        recursive=request.recursive,
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
