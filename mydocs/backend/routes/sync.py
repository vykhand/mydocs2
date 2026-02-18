"""Sync API routes — storage-to-DB synchronization."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from tinystructlog import get_logger

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
