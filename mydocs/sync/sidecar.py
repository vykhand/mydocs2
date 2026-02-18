"""Sidecar read/write utilities for sync."""

from mydocs.models import Document, MetadataSidecar
from mydocs.parsing.storage.local import LocalFileStorage


def build_sidecar_from_document(doc: Document) -> MetadataSidecar:
    """Construct a MetadataSidecar from an existing Document."""
    return MetadataSidecar(
        storage_backend=doc.storage_backend,
        original_path=doc.original_path,
        original_file_name=doc.original_file_name,
        file_type=doc.file_type,
        storage_mode=doc.storage_mode,
        managed_path=doc.managed_path,
        file_metadata=doc.file_metadata,
        document_type=doc.document_type,
        tags=doc.tags,
        status=doc.status,
        parser_engine=doc.parser_engine,
        parser_config_hash=doc.parser_config_hash,
        created_at=doc.created_at,
        modified_at=doc.modified_at,
    )


async def write_sidecar(doc: Document, storage: LocalFileStorage) -> str:
    """Write a metadata sidecar for a document to managed storage.

    Returns:
        Path to the written sidecar file.
    """
    sidecar = build_sidecar_from_document(doc)
    sidecar_data = sidecar.model_dump(exclude_none=True)
    return await storage.write_managed_sidecar(doc.id, sidecar_data)


async def read_sidecar(sidecar_path: str, storage: LocalFileStorage) -> MetadataSidecar:
    """Read and parse a metadata sidecar file.

    Returns:
        Parsed MetadataSidecar instance.
    """
    data = await storage.read_sidecar(sidecar_path)
    return MetadataSidecar(**data)
