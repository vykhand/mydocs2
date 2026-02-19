"""Scan managed storage and database to build a sync plan."""

import os
from collections import Counter
from datetime import datetime

from tinystructlog import get_logger

import mydocs.config as C
from mydocs.models import Document, MetadataSidecar, StorageBackendEnum
from mydocs.parsing.pipeline import EXTENSION_MAP
from mydocs.parsing.storage import get_storage
from mydocs.sync.models import SyncAction, SyncItem, SyncPlan

log = get_logger(__name__)

# Extensions recognized as managed document files (derived from EXTENSION_MAP)
_MANAGED_EXTENSIONS = set(EXTENSION_MAP.keys())


def _doc_id_from_filename(filename: str) -> str | None:
    """Extract doc_id from a managed filename like '<doc_id>.<ext>'.

    Returns None if the file is not a recognized managed document file
    (e.g., .di.json caches, .gitkeep, embedding caches).
    """
    if filename.endswith(".metadata.json"):
        return None
    if filename.startswith("."):
        return None
    stem, ext = os.path.splitext(filename)
    if ext.lower() not in _MANAGED_EXTENSIONS:
        return None
    return stem


async def scan_managed_storage(
    scan_path: str | None = None,
    storage_backend: StorageBackendEnum | None = None,
) -> dict[str, dict]:
    """Scan managed storage for files and their sidecars.

    Returns:
        Dict keyed by doc_id with:
            file_path: str - path to the managed file
            sidecar_path: str | None - path to the sidecar, if it exists
            sidecar: MetadataSidecar | None - parsed sidecar, if it exists
    """
    backend = storage_backend or StorageBackendEnum(C.STORAGE_BACKEND)

    if backend == StorageBackendEnum.AZURE_BLOB:
        return await _scan_blob_storage(backend)

    # Local storage scan
    managed_root = scan_path or os.path.join(C.DATA_FOLDER, "managed")

    if not os.path.isdir(managed_root):
        log.warning(f"Managed storage directory does not exist: {managed_root}")
        return {}

    storage = get_storage(backend, managed_root=managed_root)
    entries = os.listdir(managed_root)

    # Index sidecar files by doc_id
    sidecar_map: dict[str, str] = {}
    for entry in entries:
        if entry.endswith(".metadata.json"):
            doc_id = entry.removesuffix(".metadata.json")
            sidecar_map[doc_id] = os.path.join(managed_root, entry)

    # Index managed files by doc_id
    result: dict[str, dict] = {}
    for entry in entries:
        if entry.endswith(".metadata.json"):
            continue
        full_path = os.path.join(managed_root, entry)
        if not os.path.isfile(full_path):
            continue
        doc_id = _doc_id_from_filename(entry)
        if not doc_id:
            continue

        sidecar_path = sidecar_map.get(doc_id)
        sidecar = None
        if sidecar_path:
            try:
                data = await storage.read_sidecar(sidecar_path)
                sidecar = MetadataSidecar(**data)
            except Exception as e:
                log.warning(f"Failed to read sidecar {sidecar_path}: {e}")

        result[doc_id] = {
            "file_path": full_path,
            "sidecar_path": sidecar_path,
            "sidecar": sidecar,
        }

    log.info(f"Scanned {len(result)} files in managed storage ({managed_root})")
    return result


async def _scan_blob_storage(backend: StorageBackendEnum) -> dict[str, dict]:
    """Scan Azure Blob Storage container for files and sidecars."""
    storage = get_storage(backend)
    blobs = await storage.list_files()

    # Index sidecars by doc_id
    sidecar_map: dict[str, dict] = {}
    for blob in blobs:
        if blob["name"].endswith(".metadata.json"):
            doc_id = blob["name"].removesuffix(".metadata.json")
            sidecar_map[doc_id] = blob["path"]

    # Index managed files by doc_id
    result: dict[str, dict] = {}
    for blob in blobs:
        if blob["name"].endswith(".metadata.json"):
            continue
        doc_id = _doc_id_from_filename(blob["name"])
        if not doc_id:
            continue

        sidecar_path = sidecar_map.get(doc_id)
        sidecar = None
        if sidecar_path:
            try:
                data = await storage.read_sidecar(sidecar_path)
                sidecar = MetadataSidecar(**data)
            except Exception as e:
                log.warning(f"Failed to read blob sidecar {sidecar_path}: {e}")

        result[doc_id] = {
            "file_path": blob["path"],
            "sidecar_path": sidecar_path,
            "sidecar": sidecar,
        }

    log.info(f"Scanned {len(result)} blobs in Azure Blob Storage")
    return result


async def scan_db_documents() -> dict[str, Document]:
    """Query all documents from the database, indexed by ID."""
    docs = await Document.afind({})
    result = {doc.id: doc for doc in docs}
    log.info(f"Found {len(result)} documents in database")
    return result


async def build_sync_plan(
    scan_path: str | None = None,
    verify_content: bool = False,
    storage_backend: StorageBackendEnum | None = None,
) -> SyncPlan:
    """Compare managed storage with database and build a sync plan.

    Args:
        scan_path: Override for managed storage path (local backend only).
        verify_content: If True, verify file content via SHA256 comparison.
        storage_backend: Storage backend to use. Defaults to config.

    Returns:
        SyncPlan with items and summary counts.
    """
    backend = storage_backend or StorageBackendEnum(C.STORAGE_BACKEND)
    managed_root = scan_path or os.path.join(C.DATA_FOLDER, "managed")
    disk_files = await scan_managed_storage(scan_path, storage_backend=backend)
    db_docs = await scan_db_documents()

    items: list[SyncItem] = []
    storage = get_storage(backend, managed_root=managed_root) if backend == StorageBackendEnum.LOCAL else get_storage(backend)

    # Check each file on disk against DB
    for doc_id, disk_info in disk_files.items():
        file_path = disk_info["file_path"]
        sidecar_path = disk_info["sidecar_path"]
        sidecar: MetadataSidecar | None = disk_info["sidecar"]
        db_doc = db_docs.get(doc_id)

        if sidecar and not db_doc:
            # File + sidecar on disk, no DB record → restore
            items.append(SyncItem(
                file_path=file_path,
                doc_id=doc_id,
                action=SyncAction.restore,
                reason="File and sidecar on disk, no DB record",
                sidecar_path=sidecar_path,
            ))
        elif sidecar and db_doc:
            # Both exist — check content integrity
            if verify_content and sidecar.file_metadata and db_doc.file_metadata:
                disk_sha = sidecar.file_metadata.sha256
                db_sha = db_doc.file_metadata.sha256 if db_doc.file_metadata else None
                if disk_sha and db_sha and disk_sha != db_sha:
                    items.append(SyncItem(
                        file_path=file_path,
                        doc_id=doc_id,
                        action=SyncAction.reparse,
                        reason=f"SHA256 mismatch: disk={disk_sha[:12]}... db={db_sha[:12]}...",
                        sidecar_path=sidecar_path,
                    ))
                    continue
            items.append(SyncItem(
                file_path=file_path,
                doc_id=doc_id,
                action=SyncAction.verified,
                reason="File, sidecar, and DB record present",
                sidecar_path=sidecar_path,
            ))
        elif not sidecar and db_doc:
            # File on disk, no sidecar, has DB record → write sidecar
            items.append(SyncItem(
                file_path=file_path,
                doc_id=doc_id,
                action=SyncAction.sidecar_missing,
                reason="File and DB record present, sidecar missing — will write from DB",
            ))
        else:
            # File on disk, no sidecar, no DB record → cannot auto-restore
            items.append(SyncItem(
                file_path=file_path,
                doc_id=doc_id,
                action=SyncAction.sidecar_missing,
                reason="File on disk, no sidecar and no DB record — manual intervention needed",
            ))

    # Check DB records that have no file on disk
    for doc_id, db_doc in db_docs.items():
        if doc_id not in disk_files:
            items.append(SyncItem(
                doc_id=doc_id,
                action=SyncAction.orphaned_db,
                reason=f"DB record exists, no file on disk (original: {db_doc.original_file_name})",
            ))

    # Build summary
    summary = dict(Counter(item.action.value for item in items))

    plan = SyncPlan(
        items=items,
        summary=summary,
        scan_path=managed_root,
        scanned_at=datetime.now(),
    )

    log.info(f"Sync plan built: {summary}")
    return plan
