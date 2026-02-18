# Sync Specification

**Package**: `mydocs.sync`
**Version**: 1.0
**Status**: Draft

**Related Specs**: [parsing-engine.md](parsing-engine.md) (data models, pipeline, storage), [backend.md](backend.md) (HTTP API), [cli.md](cli.md) (CLI interface)

---

## 1. Overview

The sync module enables rebuilding the database from managed storage when the database is lost, corrupted, or switched to a new backend. It reads metadata sidecar files and cached parse results from disk to reconstruct `Document`, `DocumentPage`, and `DocumentElement` records.

The sync process works in three phases:
1. **Scan & Plan** (read-only): discover files and sidecars in storage, compare with DB state
2. **Execute**: perform restore, reparse, and cleanup actions
3. **Report**: return per-item results and summary counts

---

## 2. Metadata Sidecar

### 2.1 MetadataSidecar Model

The `MetadataSidecar` model lives in `mydocs/models.py` alongside `Document` and `FileMetadata`, since both the parsing engine (writes sidecars) and sync module (reads sidecars) depend on it.

```python
class MetadataSidecar(BaseModel):
    """Metadata sidecar written alongside managed/external files for DB recovery."""

    # Identity (used to recompute document ID via composite key)
    storage_backend: StorageBackendEnum
    original_path: str

    # File info
    original_file_name: str
    file_type: FileTypeEnum
    storage_mode: StorageModeEnum
    managed_path: Optional[str] = None

    # Full file metadata (sha256, crc32, size, timestamps, etc.)
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
```

### 2.2 Sidecar File Format

- **Filename**: `<doc_id>.metadata.json` (same convention as external mode sidecars)
- **Location**:
  - Managed mode: in `data/managed/` alongside the managed file
  - External mode: alongside the original file (existing behavior)
- **Format**: JSON, human-readable with indent=2
- **Encoding**: UTF-8

### 2.3 Sidecar Writing

Sidecars are written during ingestion for **both** storage modes:
- **Managed mode**: sidecar written to `data/managed/<doc_id>.metadata.json` (new behavior)
- **External mode**: sidecar written to `<source_dir>/<doc_id>.metadata.json` (existing behavior, enhanced with full MetadataSidecar fields)

The `MetadataSidecar` is constructed from the `Document` model after ingestion, ensuring all fields are populated.

---

## 3. Sync Data Models

Sync-specific data models live in `mydocs/sync/models.py`.

### 3.1 SyncAction Enum

```python
class SyncAction(StrEnum):
    restore = "restore"               # File + sidecar on disk, no DB record → restore from sidecar
    reparse = "reparse"               # File on disk, DB record exists but content hash mismatch → reparse
    orphaned_db = "orphaned_db"       # DB record exists, no file on disk → flag as orphaned
    verified = "verified"             # File + sidecar + DB record match → no action needed
    sidecar_missing = "sidecar_missing"  # File on disk, no sidecar → cannot auto-restore
```

### 3.2 SyncItem

```python
class SyncItem(BaseModel):
    file_path: Optional[str] = None   # Path to the file on disk (None for orphaned_db)
    doc_id: str                        # Document ID (computed or from DB)
    action: SyncAction
    reason: str                        # Human-readable explanation
    sidecar_path: Optional[str] = None # Path to sidecar file (if exists)
```

### 3.3 SyncPlan

```python
class SyncPlan(BaseModel):
    items: List[SyncItem] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)  # {action: count}
    scan_path: str                     # Path that was scanned
    scanned_at: datetime
```

### 3.4 SyncReport

```python
class SyncReport(BaseModel):
    items: List[SyncItemResult] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)  # {action: {success: N, failed: N}}
    started_at: datetime
    completed_at: datetime

class SyncItemResult(BaseModel):
    item: SyncItem
    success: bool
    error: Optional[str] = None
```

---

## 4. Sync Algorithm

### 4.1 Scan & Plan Phase

1. **Scan managed storage** (`data/managed/`):
   - List all files (excluding `.metadata.json` sidecars)
   - For each file, look for a corresponding `<doc_id>.metadata.json`
   - Parse sidecar if found → `MetadataSidecar`

2. **Scan database**:
   - Query all documents from the `documents` collection
   - Index by document ID for fast lookup

3. **Build diff** — for each file on disk:
   - **Has sidecar + no DB record** → `restore` (restore document from sidecar)
   - **Has sidecar + DB record + SHA256 matches** → `verified`
   - **Has sidecar + DB record + SHA256 mismatch** → `reparse`
   - **No sidecar + no DB record** → `sidecar_missing` (cannot auto-restore)
   - **No sidecar + has DB record** → `sidecar_missing` (write sidecar from DB)

4. **For each DB record without a file on disk** → `orphaned_db`

### 4.2 Execute Phase

For each `SyncItem` in the plan:

- **`restore`**: Read sidecar → construct `Document` → `asave()` to DB → if `.di.json` cache exists alongside the managed file, run parser with `use_cache=True` to rebuild pages/elements
- **`reparse`**: Update `file_metadata` from disk → re-run parse pipeline
- **`sidecar_missing`** (with DB record): Query document from DB → write sidecar to disk
- **`sidecar_missing`** (without DB record): Log warning, skip (requires manual intervention)
- **`orphaned_db`**: Add `_orphaned` tag to the document
- **`verified`**: No action

### 4.3 Report Phase

Return a `SyncReport` with per-item results (success/failure/error) and summary counts.

---

## 5. CLI Commands

### 5.1 `mydocs sync status`

Scan storage and DB, display a sync plan without executing.

```
mydocs sync status
    --scan-path PATH            # Override managed storage path (default: data/managed/)
    --verify-content            # Verify file content via SHA256 (slower)
    --output json|table|quiet   # Output format (default: table)
```

### 5.2 `mydocs sync run`

Execute a sync plan.

```
mydocs sync run
    --scan-path PATH            # Override managed storage path (default: data/managed/)
    --verify-content            # Verify file content via SHA256
    --reparse                   # Re-parse documents with cache mismatches
    --actions restore,sidecar_missing  # Comma-separated actions to execute (default: all)
    --dry-run                   # Show plan without executing
    --output json|table|quiet   # Output format (default: table)
```

### 5.3 `mydocs sync write-sidecars`

Write sidecars for all managed files that have DB records but no sidecars.

```
mydocs sync write-sidecars
    --scan-path PATH            # Override managed storage path (default: data/managed/)
    --output json|table|quiet   # Output format (default: table)
```

---

## 6. API Endpoints

### 6.1 Build Sync Plan

```
POST /api/v1/sync/plan
Body: {
    "scan_path": "data/managed/",     // Optional override
    "verify_content": false           // Optional SHA256 verification
}
Response: { ... SyncPlan model ... }
```

### 6.2 Execute Sync

```
POST /api/v1/sync/execute
Body: {
    "scan_path": "data/managed/",     // Optional override
    "verify_content": false,          // Optional SHA256 verification
    "reparse": false,                 // Re-parse on mismatch
    "actions": ["restore", "sidecar_missing"]  // Optional action filter
}
Response: { ... SyncReport model ... }
```

### 6.3 Write Sidecars

```
POST /api/v1/sync/write-sidecars
Body: {
    "scan_path": "data/managed/"      // Optional override
}
Response: {
    "written": 5,
    "skipped": 2
}
```

---

## 7. Package Structure

```
mydocs/
  sync/
    __init__.py
    models.py           # SyncAction, SyncItem, SyncPlan, SyncReport, SyncItemResult
    sidecar.py          # write_sidecar(), read_sidecar()
    scanner.py          # scan_managed_storage(), scan_db_documents(), build_sync_plan()
    reconciler.py       # execute_sync_plan()
```

---

## 8. Dependencies

No additional dependencies. The sync module uses:
- `mydocs.models` — `Document`, `DocumentPage`, `FileMetadata`, `MetadataSidecar`, enums
- `mydocs.parsing.pipeline` — `parse_document()` for re-parsing
- `mydocs.parsing.storage.local` — `LocalFileStorage` for file operations
- `lightodm` — database operations (transitive)
- `aiofiles` — async file I/O (transitive)
