"""Sync API routes — storage-to-DB synchronization."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from tinystructlog import get_logger

from mydocs.models import StorageBackendEnum
from mydocs.sync.models import SyncAction
from mydocs.sync.reconciler import execute_sync_plan
from mydocs.sync.scanner import build_sync_plan

log = get_logger(__name__)

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


class SyncPlanRequest(BaseModel):
    scan_path: Optional[str] = None
    verify_content: bool = False


class SyncExecuteRequest(BaseModel):
    scan_path: Optional[str] = None
    verify_content: bool = False
    reparse: bool = False
    actions: Optional[List[str]] = None


class WriteSidecarsRequest(BaseModel):
    scan_path: Optional[str] = None


class MigratePlanRequest(BaseModel):
    source_backend: str
    target_backend: str


class MigrateExecuteRequest(BaseModel):
    source_backend: str
    target_backend: str
    delete_source: bool = False


@router.post("/plan")
async def create_sync_plan(request: SyncPlanRequest):
    """Build a sync plan by scanning storage and comparing with DB."""
    try:
        plan = await build_sync_plan(
            scan_path=request.scan_path,
            verify_content=request.verify_content,
        )
        return plan.model_dump()
    except Exception as e:
        log.error(f"Failed to build sync plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_sync(request: SyncExecuteRequest):
    """Execute a sync plan."""
    try:
        plan = await build_sync_plan(
            scan_path=request.scan_path,
            verify_content=request.verify_content,
        )
        report = await execute_sync_plan(
            plan=plan,
            reparse=request.reparse,
            actions=request.actions,
        )
        return report.model_dump()
    except Exception as e:
        log.error(f"Sync execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/write-sidecars")
async def write_sidecars(request: WriteSidecarsRequest):
    """Write missing sidecars for managed files that have DB records."""
    try:
        plan = await build_sync_plan(scan_path=request.scan_path)
        report = await execute_sync_plan(
            plan=plan,
            actions=["sidecar_missing"],
        )

        written = sum(
            1 for r in report.items
            if r.success and r.item.action == SyncAction.sidecar_missing
        )
        skipped = sum(
            1 for r in report.items
            if not r.success and r.item.action == SyncAction.sidecar_missing
        )

        return {"written": written, "skipped": skipped}
    except Exception as e:
        log.error(f"Write sidecars failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migrate/plan")
async def create_migrate_plan(request: MigratePlanRequest):
    """Build a migration plan for cross-backend document migration."""
    from mydocs.sync.migrator import build_migrate_plan

    try:
        source = StorageBackendEnum(request.source_backend)
        target = StorageBackendEnum(request.target_backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid backend: {e}")

    if source == target:
        raise HTTPException(status_code=400, detail="source_backend and target_backend must be different")

    try:
        plan = await build_migrate_plan(source, target)
        return plan.model_dump()
    except Exception as e:
        log.error(f"Failed to build migrate plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migrate/execute")
async def execute_migrate(request: MigrateExecuteRequest):
    """Execute a cross-backend migration (storage-only, no DB writes)."""
    from mydocs.parsing.storage import get_storage
    from mydocs.sync.migrator import build_migrate_plan, execute_migrate_plan

    try:
        source = StorageBackendEnum(request.source_backend)
        target = StorageBackendEnum(request.target_backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid backend: {e}")

    if source == target:
        raise HTTPException(status_code=400, detail="source_backend and target_backend must be different")

    try:
        plan = await build_migrate_plan(source, target)
        source_storage = get_storage(source)
        dest_storage = get_storage(target)
        report = await execute_migrate_plan(
            plan=plan,
            source_storage=source_storage,
            dest_storage=dest_storage,
            delete_source=request.delete_source,
        )
        return report.model_dump()
    except Exception as e:
        log.error(f"Migration execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
