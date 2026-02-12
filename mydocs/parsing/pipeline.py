import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from tinystructlog import get_logger, set_log_context

import mydocs.config as C
from mydocs.parsing.azure_di.parser import AzureDIDocumentParser
from mydocs.parsing.base_parser import DocumentLockedException
from mydocs.parsing.config import ParserConfig
from mydocs.models import (
    Document,
    DocumentStatusEnum,
    FileTypeEnum,
    StorageBackendEnum,
    StorageModeEnum,
)
from mydocs.parsing.storage.local import LocalFileStorage

log = get_logger(__name__)

# Extension to FileTypeEnum mapping
EXTENSION_MAP: dict[str, FileTypeEnum] = {
    ".pdf": FileTypeEnum.PDF,
    ".txt": FileTypeEnum.TXT,
    ".docx": FileTypeEnum.DOCX,
    ".xlsx": FileTypeEnum.XLSX,
    ".pptx": FileTypeEnum.PPTX,
    ".jpeg": FileTypeEnum.JPEG,
    ".jpg": FileTypeEnum.JPEG,
    ".png": FileTypeEnum.PNG,
    ".bmp": FileTypeEnum.BMP,
    ".tiff": FileTypeEnum.TIFF,
    ".tif": FileTypeEnum.TIFF,
}

# File types supported for parsing in P0
SUPPORTED_FILE_TYPES = {FileTypeEnum.PDF}


def detect_file_type(path: str) -> FileTypeEnum:
    """Detect file type from extension."""
    ext = os.path.splitext(path)[1].lower()
    return EXTENSION_MAP.get(ext, FileTypeEnum.UNKNOWN)


def discover_files(source: str, recursive: bool = True) -> list[Path]:
    """Discover files from a path (file or directory)."""
    source_path = Path(source)

    if source_path.is_file():
        return [source_path]

    if source_path.is_dir():
        if recursive:
            return [p for p in source_path.rglob("*") if p.is_file()]
        return [p for p in source_path.iterdir() if p.is_file()]

    log.warning(f"Source path does not exist: {source}")
    return []


async def ingest_files(
    source: str | list[str],
    storage_mode: StorageModeEnum = StorageModeEnum.MANAGED,
    tags: list[str] | None = None,
    recursive: bool = True,
) -> tuple[list[Document], list[dict]]:
    """
    Ingest files from a source path or list of paths.

    Returns:
        Tuple of (ingested documents, skipped files with reasons)
    """
    tags = tags or []
    documents = []
    skipped = []

    # Normalize to list of sources
    sources = [source] if isinstance(source, str) else source

    # Discover all files
    all_files: list[Path] = []
    for src in sources:
        all_files.extend(discover_files(src, recursive=recursive))

    log.info(f"Discovered {len(all_files)} files from {len(sources)} source(s)")

    storage = LocalFileStorage()

    for file_path in all_files:
        file_type = detect_file_type(str(file_path))

        if file_type == FileTypeEnum.UNKNOWN:
            skipped.append({"path": str(file_path), "reason": "unknown_format"})
            continue

        if file_type not in SUPPORTED_FILE_TYPES:
            # Record unsupported but known formats
            doc = Document(
                file_name=file_path.name,
                original_file_name=file_path.name,
                file_type=file_type,
                original_path=str(file_path.resolve()),
                storage_mode=storage_mode,
                storage_backend=StorageBackendEnum.LOCAL,
                status=DocumentStatusEnum.NOT_SUPPORTED,
                tags=tags,
                created_at=datetime.now(),
            )
            await doc.asave()
            skipped.append({"path": str(file_path), "reason": "unsupported_format"})
            continue

        set_log_context(file_name=file_path.name)
        log.info(f"Ingesting file: {file_path.name}")

        # Compute file metadata
        file_metadata = await storage.get_file_metadata(str(file_path))
        mime_type, _ = mimetypes.guess_type(str(file_path))
        file_metadata.mime_type = mime_type

        # Create Document first to get deterministic ID (from composite key)
        doc = Document(
            file_name=file_path.name,  # temporary, updated below for managed mode
            original_file_name=file_path.name,
            file_type=file_type,
            original_path=str(file_path.resolve()),
            storage_mode=storage_mode,
            storage_backend=StorageBackendEnum.LOCAL,
            file_metadata=file_metadata,
            status=DocumentStatusEnum.NEW,
            tags=tags,
            created_at=datetime.now(),
        )
        # doc.id is now computed from composite key [storage_backend, original_path]

        if storage_mode == StorageModeEnum.MANAGED:
            managed_path, managed_file_name = await storage.copy_to_managed(str(file_path), doc.id)
            doc.managed_path = managed_path
            doc.file_name = managed_file_name
        else:
            # External mode: write sidecar metadata file as <id>.metadata.json
            sidecar_data = file_metadata.model_dump(exclude_none=True)
            sidecar_data["original_file_name"] = file_path.name
            sidecar_data["original_path"] = str(file_path.resolve())
            await storage.write_metadata_sidecar(str(file_path), doc.id, sidecar_data)

        await doc.asave()
        documents.append(doc)
        log.info(f"Ingested document {doc.id} for file {file_path.name} -> {doc.file_name}")

    log.info(f"Ingestion complete: {len(documents)} ingested, {len(skipped)} skipped")
    return documents, skipped


async def parse_document(
    document_id: str,
    parser_config_override: dict | None = None,
) -> Document:
    """Parse a single document by ID."""
    document = await Document.aget(document_id)
    if not document:
        raise ValueError(f"Document {document_id} not found")

    set_log_context(document_id=document.id, file_name=document.file_name)

    parser_config = ParserConfig()
    if parser_config_override:
        override = ParserConfig(**parser_config_override, _is_internal_load=True)
        parser_config = parser_config.apply_config(override)

    async with AzureDIDocumentParser(document=document, parser_config=parser_config) as parser:
        document = await parser.parse()

    log.info(f"Parsed document {document.id}, elements: {len(document.elements or [])}")
    return document


async def batch_parse(
    document_ids: list[str] | None = None,
    tags: list[str] | None = None,
    status_filter: str | None = None,
) -> tuple[int, int]:
    """
    Parse multiple documents matching the given criteria.

    Returns:
        Tuple of (queued count, skipped count)
    """
    filter_query: dict = {}

    if document_ids:
        filter_query["_id"] = {"$in": document_ids}
    if tags:
        filter_query["tags"] = {"$all": tags}
    if status_filter:
        filter_query["status"] = status_filter
    else:
        filter_query.setdefault("status", DocumentStatusEnum.NEW)

    documents = await Document.afind(filter_query)
    log.info(f"Found {len(documents)} documents to parse")

    queued = 0
    skipped = 0

    for doc in documents:
        try:
            await parse_document(doc.id)
            queued += 1
        except DocumentLockedException:
            log.warning(f"Document {doc.id} is locked. Skipping.")
            skipped += 1
        except Exception as e:
            log.error(f"Error parsing document {doc.id}: {e}", exc_info=True)
            skipped += 1

    log.info(f"Batch parse complete: {queued} parsed, {skipped} skipped")
    return queued, skipped
