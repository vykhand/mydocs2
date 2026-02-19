"""Cross-backend storage migration — plan and execute."""

from collections import defaultdict
from datetime import datetime

from tinystructlog import get_logger

from mydocs.models import Document, StorageBackendEnum, StorageModeEnum
from mydocs.parsing.storage.base import FileStorage
from mydocs.sync.models import (
    MigrateAction,
    MigrateItem,
    MigrateItemResult,
    MigratePlan,
    MigrateReport,
)

log = get_logger(__name__)


async def build_migrate_plan(
    source_backend: StorageBackendEnum,
    target_backend: StorageBackendEnum,
) -> MigratePlan:
    """Build a migration plan by reading the DB (read-only).

    Classifies each document as:
    - copy: managed + on source backend → copy file + sidecar
    - copy_sidecar: external + on source backend → copy sidecar only
    - skip_already_on_target: already on target backend
    - skip_no_managed_path: managed mode but no managed_path
    """
    documents = await Document.afind({})
    items: list[MigrateItem] = []
    counts: dict[str, int] = defaultdict(int)

    for doc in documents:
        if doc.storage_backend == target_backend:
            action = MigrateAction.skip_already_on_target
            items.append(MigrateItem(
                doc_id=doc.id,
                file_name=doc.file_name,
                source_path=doc.managed_path or doc.original_path,
                storage_mode=doc.storage_mode.value,
                action=action,
                reason=f"Already on {target_backend.value}",
            ))
            counts[action.value] += 1
            continue

        if doc.storage_backend != source_backend:
            # Document is on a third backend — skip
            continue

        if doc.storage_mode == StorageModeEnum.MANAGED:
            if not doc.managed_path:
                action = MigrateAction.skip_no_managed_path
                items.append(MigrateItem(
                    doc_id=doc.id,
                    file_name=doc.file_name,
                    source_path=doc.original_path,
                    storage_mode=doc.storage_mode.value,
                    action=action,
                    reason="No managed_path to copy from",
                ))
                counts[action.value] += 1
            else:
                action = MigrateAction.copy
                items.append(MigrateItem(
                    doc_id=doc.id,
                    file_name=doc.file_name,
                    source_path=doc.managed_path,
                    storage_mode=doc.storage_mode.value,
                    action=action,
                    reason=f"Copy file + sidecar from {source_backend.value} to {target_backend.value}",
                ))
                counts[action.value] += 1
        else:
            # External mode — copy sidecar only
            action = MigrateAction.copy_sidecar
            items.append(MigrateItem(
                doc_id=doc.id,
                file_name=doc.file_name,
                source_path=doc.original_path,
                storage_mode=doc.storage_mode.value,
                action=action,
                reason=f"Copy sidecar from {source_backend.value} to {target_backend.value}",
            ))
            counts[action.value] += 1

    return MigratePlan(
        items=items,
        summary=dict(counts),
        source_backend=source_backend.value,
        target_backend=target_backend.value,
        planned_at=datetime.now(),
    )


async def execute_migrate_plan(
    plan: MigratePlan,
    source_storage: FileStorage,
    dest_storage: FileStorage,
    delete_source: bool = False,
) -> MigrateReport:
    """Execute a migration plan — storage-only, no DB writes.

    For 'copy' items (managed): download file + read sidecar from source,
    upload file + write updated sidecar to target.

    For 'copy_sidecar' items (external): read sidecar from source,
    update storage_backend, write to target managed storage.

    After migration, rebuild DB via: mydocs sync run --backend <target>
    """
    started_at = datetime.now()
    results: list[MigrateItemResult] = []
    target_backend = plan.target_backend

    for item in plan.items:
        if item.action in (
            MigrateAction.skip_already_on_target,
            MigrateAction.skip_no_managed_path,
        ):
            results.append(MigrateItemResult(item=item, success=True))
            continue

        try:
            if item.action == MigrateAction.copy:
                dest_path = await _copy_managed(
                    item, source_storage, dest_storage, target_backend, delete_source,
                )
                results.append(MigrateItemResult(
                    item=item, success=True, dest_path=dest_path,
                ))

            elif item.action == MigrateAction.copy_sidecar:
                dest_path = await _copy_sidecar_only(
                    item, source_storage, dest_storage, target_backend, delete_source,
                )
                results.append(MigrateItemResult(
                    item=item, success=True, dest_path=dest_path,
                ))

        except Exception as e:
            log.error(f"Migration failed for {item.doc_id}: {e}")
            results.append(MigrateItemResult(
                item=item, success=False, error=str(e),
            ))

    completed_at = datetime.now()

    summary: dict = defaultdict(lambda: {"success": 0, "failed": 0})
    for r in results:
        key = r.item.action.value
        if r.success:
            summary[key]["success"] += 1
        else:
            summary[key]["failed"] += 1

    return MigrateReport(
        items=results,
        summary=dict(summary),
        source_backend=plan.source_backend,
        target_backend=plan.target_backend,
        started_at=started_at,
        completed_at=completed_at,
        delete_source=delete_source,
    )


async def _copy_managed(
    item: MigrateItem,
    source_storage: FileStorage,
    dest_storage: FileStorage,
    target_backend: str,
    delete_source: bool,
) -> str:
    """Copy a managed file + its sidecar to the target backend."""
    # 1. Download file bytes from source
    data = await source_storage.get_file_bytes(item.source_path)
    log.info(f"Downloaded {len(data)} bytes for {item.doc_id} from source")

    # 2. Upload file to target
    dest_path = await dest_storage.write_managed_bytes(
        item.doc_id, item.file_name, data,
    )
    log.info(f"Uploaded {item.doc_id} to target: {dest_path}")

    # 3. Read sidecar from source, update, write to target
    sidecar_path = _sidecar_path_for_managed(item.source_path, item.doc_id)
    try:
        sidecar_data = await source_storage.read_sidecar(sidecar_path)
    except Exception:
        # Sidecar might be stored with doc_id prefix in managed storage
        sidecar_data = await source_storage.read_sidecar(
            _sidecar_path_by_doc_id(item.source_path, item.doc_id)
        )

    sidecar_data["storage_backend"] = target_backend
    sidecar_data["managed_path"] = dest_path
    await dest_storage.write_managed_sidecar(item.doc_id, sidecar_data)
    log.info(f"Wrote sidecar for {item.doc_id} to target")

    # 4. Optionally delete source
    if delete_source:
        try:
            await source_storage.delete_file(item.source_path)
            await source_storage.delete_file(sidecar_path)
            log.info(f"Deleted source files for {item.doc_id}")
        except Exception as e:
            log.warning(f"Failed to delete source for {item.doc_id}: {e}")

    return dest_path


async def _copy_sidecar_only(
    item: MigrateItem,
    source_storage: FileStorage,
    dest_storage: FileStorage,
    target_backend: str,
    delete_source: bool,
) -> str:
    """Copy an external document's sidecar to the target backend's managed storage."""
    # External sidecars are stored next to the original file
    # Try reading from source storage (could be local path)
    import os
    sidecar_filename = f"{item.doc_id}.metadata.json"
    sidecar_path = os.path.join(os.path.dirname(item.source_path), sidecar_filename)

    sidecar_data = await source_storage.read_sidecar(sidecar_path)
    sidecar_data["storage_backend"] = target_backend
    dest_path = await dest_storage.write_managed_sidecar(item.doc_id, sidecar_data)
    log.info(f"Wrote external sidecar for {item.doc_id} to target: {dest_path}")

    if delete_source:
        try:
            await source_storage.delete_file(sidecar_path)
            log.info(f"Deleted source sidecar for {item.doc_id}")
        except Exception as e:
            log.warning(f"Failed to delete source sidecar for {item.doc_id}: {e}")

    return dest_path


def _sidecar_path_for_managed(managed_path: str, doc_id: str) -> str:
    """Derive the sidecar path from the managed file path.

    Managed sidecars are in the same directory as the file, named <doc_id>.metadata.json.
    For az:// URIs, replace the blob name. For local, replace in the same dir.
    """
    if managed_path.startswith("az://"):
        # az://container/blob_name → az://container/<doc_id>.metadata.json
        parts = managed_path.split("/")
        parts[-1] = f"{doc_id}.metadata.json"
        return "/".join(parts)
    else:
        import os
        return os.path.join(os.path.dirname(managed_path), f"{doc_id}.metadata.json")


def _sidecar_path_by_doc_id(managed_path: str, doc_id: str) -> str:
    """Alternative sidecar path lookup."""
    return _sidecar_path_for_managed(managed_path, doc_id)
