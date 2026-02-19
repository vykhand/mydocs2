"""Execute sync plans — restore, reparse, write sidecars, flag orphans."""

from collections import defaultdict
from datetime import datetime

from tinystructlog import get_logger

import mydocs.config as C
from mydocs.models import Document, DocumentStatusEnum, MetadataSidecar, StorageBackendEnum
from mydocs.parsing.pipeline import parse_document
from mydocs.parsing.storage import get_storage
from mydocs.parsing.storage.base import FileStorage
from mydocs.sync.models import SyncAction, SyncItemResult, SyncPlan, SyncReport
from mydocs.sync.sidecar import build_sidecar_from_document, read_sidecar, write_sidecar

log = get_logger(__name__)


async def _restore_from_sidecar(
    sidecar_path: str,
    file_path: str,
    storage: FileStorage,
    reparse: bool = False,
) -> None:
    """Restore a document from its sidecar and optionally reparse from cache."""
    sidecar = await read_sidecar(sidecar_path, storage)

    doc = Document(
        content_hash=sidecar.file_metadata.sha256,
        file_name=sidecar.managed_path.split("/")[-1] if sidecar.managed_path else sidecar.original_file_name,
        original_file_name=sidecar.original_file_name,
        file_type=sidecar.file_type,
        original_path=sidecar.original_path,
        storage_mode=sidecar.storage_mode,
        storage_backend=sidecar.storage_backend,
        managed_path=sidecar.managed_path,
        file_metadata=sidecar.file_metadata,
        status=sidecar.status if sidecar.status != DocumentStatusEnum.PARSING else DocumentStatusEnum.NEW,
        document_type=sidecar.document_type,
        tags=sidecar.tags,
        parser_engine=sidecar.parser_engine,
        parser_config_hash=sidecar.parser_config_hash,
        created_at=sidecar.created_at,
        modified_at=datetime.now(),
    )

    await doc.asave()
    log.info(f"Restored document {doc.id} from sidecar ({sidecar.original_file_name})")

    # If reparse requested, try to re-parse from .di.json cache
    if reparse:
        try:
            doc.status = DocumentStatusEnum.NEW
            await doc.asave()
            await parse_document(doc.id, parser_config_override={"use_cache": True})
            log.info(f"Re-parsed document {doc.id} from cache")
        except Exception as e:
            log.warning(f"Failed to re-parse document {doc.id}: {e}")
            raise


async def _write_missing_sidecar(doc_id: str, storage: FileStorage) -> None:
    """Write a sidecar for a document that exists in DB but has no sidecar on disk."""
    doc = await Document.aget(doc_id)
    if not doc:
        raise ValueError(f"Document {doc_id} not found in DB")
    await write_sidecar(doc, storage)
    log.info(f"Wrote sidecar for document {doc_id}")


async def _flag_orphaned(doc_id: str) -> None:
    """Add _orphaned tag to a DB record with no corresponding file."""
    await Document.aupdate_one(
        {"_id": doc_id},
        {"$addToSet": {"tags": "_orphaned"}},
    )
    log.info(f"Flagged document {doc_id} as orphaned")


async def execute_sync_plan(
    plan: SyncPlan,
    reparse: bool = False,
    actions: list[str] | None = None,
) -> SyncReport:
    """Execute a sync plan.

    Args:
        plan: The sync plan to execute.
        reparse: If True, re-parse documents that have cache available.
        actions: Optional list of action types to execute (default: all).

    Returns:
        SyncReport with per-item results.
    """
    started_at = datetime.now()
    results: list[SyncItemResult] = []
    managed_root = plan.scan_path
    backend = StorageBackendEnum(C.STORAGE_BACKEND)
    storage = get_storage(backend, managed_root=managed_root) if backend == StorageBackendEnum.LOCAL else get_storage(backend)

    allowed_actions = set(actions) if actions else None

    for item in plan.items:
        if allowed_actions and item.action.value not in allowed_actions:
            continue

        if item.action == SyncAction.verified:
            results.append(SyncItemResult(item=item, success=True))
            continue

        try:
            if item.action == SyncAction.restore:
                await _restore_from_sidecar(
                    item.sidecar_path,
                    item.file_path,
                    storage,
                    reparse=reparse,
                )
                results.append(SyncItemResult(item=item, success=True))

            elif item.action == SyncAction.reparse:
                await parse_document(item.doc_id, parser_config_override={"use_cache": True})
                results.append(SyncItemResult(item=item, success=True))

            elif item.action == SyncAction.sidecar_missing:
                # Only write sidecar if there's a DB record
                doc = await Document.aget(item.doc_id)
                if doc:
                    await _write_missing_sidecar(item.doc_id, storage)
                    results.append(SyncItemResult(item=item, success=True))
                else:
                    results.append(SyncItemResult(
                        item=item,
                        success=False,
                        error="No DB record and no sidecar — manual intervention needed",
                    ))

            elif item.action == SyncAction.orphaned_db:
                await _flag_orphaned(item.doc_id)
                results.append(SyncItemResult(item=item, success=True))

        except Exception as e:
            log.error(f"Sync action failed for {item.doc_id}: {e}")
            results.append(SyncItemResult(item=item, success=False, error=str(e)))

    completed_at = datetime.now()

    # Build summary: {action: {success: N, failed: N}}
    summary: dict = defaultdict(lambda: {"success": 0, "failed": 0})
    for r in results:
        key = r.item.action.value
        if r.success:
            summary[key]["success"] += 1
        else:
            summary[key]["failed"] += 1

    report = SyncReport(
        items=results,
        summary=dict(summary),
        started_at=started_at,
        completed_at=completed_at,
    )

    log.info(f"Sync execution complete: {dict(summary)}")
    return report
