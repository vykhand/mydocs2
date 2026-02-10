"""Pydantic request/response models for API contracts."""

from typing import Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str
    error_code: str
    status_code: int


class IngestRequest(BaseModel):
    source: str | list[str]
    storage_mode: str = "managed"
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
