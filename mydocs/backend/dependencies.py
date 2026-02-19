"""Pydantic request/response models for API contracts."""

from typing import Optional

from pydantic import BaseModel, Field

from mydocs.models import StorageBackendEnum, StorageModeEnum


class ErrorResponse(BaseModel):
    detail: str
    error_code: str
    status_code: int


class IngestRequest(BaseModel):
    source: str | list[str]
    storage_mode: StorageModeEnum = StorageModeEnum.MANAGED
    storage_backend: Optional[StorageBackendEnum] = None
    tags: list[str] = Field(default_factory=list)
    recursive: bool = True


class IngestResponse(BaseModel):
    documents: list[dict]
    skipped: list[dict]


class ParseRequest(BaseModel):
    parser_config_override: Optional[dict] = None


class ParseResponse(BaseModel):
    document_id: str
    status: str
    page_count: int
    element_count: int


class BatchParseRequest(BaseModel):
    document_ids: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    status_filter: Optional[str] = None


class BatchParseResponse(BaseModel):
    queued: int
    skipped: int


class TagsRequest(BaseModel):
    tags: list[str]


class DocumentListResponse(BaseModel):
    documents: list[dict]
    total: int
    page: int
    page_size: int


class CaseCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None


class CaseUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CaseDocumentsRequest(BaseModel):
    document_ids: list[str]


class CaseListResponse(BaseModel):
    cases: list[dict]
    total: int
    page: int
    page_size: int
