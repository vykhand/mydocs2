"""Canonical document and collection models for mydocs.

All document-level models (enums, embedded models, collection models) live here.
The parsing/models.py module re-exports these for backward compatibility.
"""

from datetime import datetime
from enum import StrEnum
from typing import List, Optional

from lightodm import MongoBaseModel, generate_composite_id
from pydantic import BaseModel, Field


# --- Enumerations ---

class FileTypeEnum(StrEnum):
    UNKNOWN = "unknown"
    PDF = "pdf"
    TXT = "txt"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    JPEG = "jpeg"
    PNG = "png"
    BMP = "bmp"
    TIFF = "tiff"


class StorageModeEnum(StrEnum):
    MANAGED = "managed"
    EXTERNAL = "external"


class StorageBackendEnum(StrEnum):
    LOCAL = "local"
    AZURE_BLOB = "azure_blob"
    S3 = "s3"
    GCS = "gcs"
    ONEDRIVE = "onedrive"


class DocumentStatusEnum(StrEnum):
    NEW = "new"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_SUPPORTED = "not_supported"


class DocumentElementTypeEnum(StrEnum):
    PARAGRAPH = "paragraph"
    TABLE = "table"
    KEY_VALUE_PAIR = "key_value_pair"
    IMAGE = "image"
    BARCODE = "barcode"


class DocumentTypeEnum(StrEnum):
    GENERIC = "generic"


# --- Embedded Models ---

class FileMetadata(BaseModel):
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    crc32: Optional[str] = None
    sha256: Optional[str] = None
    page_count: Optional[int] = None
    author: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None


class SubDocumentPageRef(BaseModel):
    """Reference to a single page within a sub-document."""
    document_id: str
    page_id: str
    page_number: int


class SubDocument(BaseModel):
    """A classified segment within a parent document."""
    id: str
    case_type: str
    document_type: str
    page_refs: List[SubDocumentPageRef]
    created_at: Optional[datetime] = None


class DocumentElement(BaseModel):
    id: str = Field(..., description="Globally unique element ID (deterministic hash)")
    page_id: str = Field(..., description="Reference to the page containing this element")
    page_number: int = Field(..., description="1-based page number")
    offset: int = Field(..., description="Character offset in the original content")
    short_id: Optional[str] = Field(None, description="Short element reference ID (e.g., p0, t1, kv2)")
    type: DocumentElementTypeEnum
    element_data: dict


# --- Sidecar Model ---

class MetadataSidecar(BaseModel):
    """Metadata sidecar written alongside managed/external files for DB recovery.

    Contains all fields needed to reconstruct a Document record from disk.
    Written during ingestion for both managed and external storage modes.
    """

    # Identity (used to recompute document ID via composite key)
    storage_backend: StorageBackendEnum
    original_path: str

    # File info
    original_file_name: str
    file_type: FileTypeEnum
    storage_mode: StorageModeEnum
    managed_path: Optional[str] = None

    # Full file metadata
    file_metadata: Optional[FileMetadata] = None

    # Document state
    document_type: DocumentTypeEnum = DocumentTypeEnum.GENERIC
    tags: List[str] = Field(default_factory=list)
    status: DocumentStatusEnum = DocumentStatusEnum.NEW
    parser_engine: Optional[str] = None
    parser_config_hash: Optional[str] = None

    # Timestamps
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

    # Sidecar meta (for forward compatibility)
    sidecar_version: int = 1


# --- Collection Models ---

class Document(MongoBaseModel):
    # File-level fields
    file_name: str                                      # Managed: <unique_id>.<ext>, External: original name
    original_file_name: str                             # Always the original file name
    file_type: FileTypeEnum
    original_path: str
    storage_mode: StorageModeEnum
    storage_backend: StorageBackendEnum
    managed_path: Optional[str] = None
    file_metadata: Optional[FileMetadata] = None

    # Document-level fields
    status: DocumentStatusEnum = DocumentStatusEnum.NEW
    document_type: DocumentTypeEnum = DocumentTypeEnum.GENERIC
    locked: bool = False

    content: Optional[str] = None
    content_type: Optional[str] = None
    parser_engine: Optional[str] = None
    parser_config_hash: Optional[str] = None

    elements: Optional[List[DocumentElement]] = None
    subdocuments: Optional[List[SubDocument]] = None

    tags: List[str] = Field(default_factory=list)

    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

    class Settings:
        name = "documents"
        composite_key = ["storage_backend", "original_path"]


class DocumentPage(MongoBaseModel):
    document_id: str
    page_number: int

    content: Optional[str] = None
    content_markdown: Optional[str] = None
    content_html: Optional[str] = None

    height: Optional[float] = None
    width: Optional[float] = None
    unit: Optional[str] = None

    class Settings:
        name = "pages"
        composite_key = ["document_id", "page_number"]


class Case(MongoBaseModel):
    name: str
    type: str = "generic"
    description: Optional[str] = None
    document_ids: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

    class Settings:
        name = "cases"
