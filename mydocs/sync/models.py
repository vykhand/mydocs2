"""Sync data models — actions, plans, and reports."""

from datetime import datetime
from enum import StrEnum
from typing import List, Optional

from pydantic import BaseModel, Field


class SyncAction(StrEnum):
    restore = "restore"
    reparse = "reparse"
    orphaned_db = "orphaned_db"
    verified = "verified"
    sidecar_missing = "sidecar_missing"


class SyncItem(BaseModel):
    file_path: Optional[str] = None
    doc_id: str
    action: SyncAction
    reason: str
    sidecar_path: Optional[str] = None


class SyncPlan(BaseModel):
    items: List[SyncItem] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    scan_path: str
    scanned_at: datetime


class SyncItemResult(BaseModel):
    item: SyncItem
    success: bool
    error: Optional[str] = None


class SyncReport(BaseModel):
    items: List[SyncItemResult] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    started_at: datetime
    completed_at: datetime
