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


# --- Migration Models ---

class MigrateAction(StrEnum):
    copy = "copy"                          # Managed: copy file + sidecar
    copy_sidecar = "copy_sidecar"          # External: copy sidecar only
    skip_already_on_target = "skip_target"  # Already on target backend
    skip_no_managed_path = "skip_no_path"   # No managed_path to copy from


class MigrateItem(BaseModel):
    doc_id: str
    file_name: str
    source_path: str              # current managed_path (or sidecar path for external)
    storage_mode: str             # "managed" or "external"
    action: MigrateAction
    reason: str


class MigratePlan(BaseModel):
    items: List[MigrateItem] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    source_backend: str
    target_backend: str
    planned_at: datetime


class MigrateItemResult(BaseModel):
    item: MigrateItem
    success: bool
    dest_path: Optional[str] = None
    error: Optional[str] = None


class MigrateReport(BaseModel):
    items: List[MigrateItemResult] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    source_backend: str
    target_backend: str
    started_at: datetime
    completed_at: datetime
    delete_source: bool = False
