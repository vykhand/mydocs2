# Backend API Reference

**Package**: `mydocs.backend`
**Base URL**: `http://localhost:8000`
**Spec**: [docs/specs/backend.md](specs/backend.md)

---

## Current State

The backend is a FastAPI application (`mydocs/backend/app.py`) exposing five route modules:

| Module | Prefix | File |
|--------|--------|------|
| Documents | `/api/v1/documents` | `routes/documents.py` |
| Search | `/api/v1/search` | `routes/search.py` |
| Cases | `/api/v1/cases` | `routes/cases.py` |
| Extraction | `/api/v1` | `routes/extract.py` |
| Sync | `/api/v1/sync` | `routes/sync.py` |

Request/response Pydantic models are in `mydocs/backend/dependencies.py`.
Search models are in `mydocs/retrieval/models.py`.
Extraction models are in `mydocs/extracting/models.py`.

### Application Setup

- CORS: all origins allowed (`*`)
- Lifespan: MongoDB connection init on startup, close on shutdown
- Global exception handlers for `RequestValidationError` (422) and generic `Exception` (500)

---

## Spec Deviations

> Items marked **[DEVIATION]** below are not present in the spec or differ from it.

| # | Category | Description |
|---|----------|-------------|
| D1 | Extra endpoint | `GET /api/v1/documents` — List documents with filtering/pagination. Not in spec. |
| D2 | Extra endpoint | `POST /api/v1/documents/upload` — Multipart file upload. Not in spec. |
| D3 | Extra endpoint | `GET /api/v1/documents/{document_id}/file` — Serve the raw file. Not in spec. |
| D4 | Extra endpoint | `DELETE /api/v1/documents/{document_id}` — Delete document, its pages, and managed file. Not in spec. |
| D5 | ~~Resolved~~ | `POST /api/v1/extract` — Now specified in backend spec Section 3.12. |
| D6 | ~~Resolved~~ | `GET /api/v1/field-results` — Now specified in backend spec Section 3.13. |
| D7 | ~~Resolved~~ | `POST /api/v1/split-classify` — Now specified in backend spec Section 3.14. |
| D8 | Extra endpoint | `GET /health` — Health check. Not in spec. |
| D9 | Schema change | `IngestRequest.source` accepts `str \| list[str]` in code; spec shows only `str`. |
| D10 | Extra error code | `CASE_NOT_FOUND` — used by case endpoints; not in spec error codes table. |
| D11 | Extra error code | `FILE_NOT_FOUND` — used by file download endpoint; not in spec error codes table. |
| D12 | Model difference | `Case` model has a `type` field (default `"generic"`); not mentioned in spec. |
| D13 | Extra query params | `GET /api/v1/documents` has `sort_by`, `sort_order`, `search`, `date_from`, `date_to` params not in spec. |
| D14 | Trailing slash | Search endpoint registered as `POST /api/v1/search/` (trailing slash); spec shows `/api/v1/search`. |

---

## Endpoints

### Health

#### `GET /health` **[DEVIATION D8]**

```http
GET http://localhost:8000/health
```

**Response** `200`:
```json
{ "status": "ok" }
```

---

### Documents

#### `GET /api/v1/documents` **[DEVIATION D1, D13]**

List documents with optional filtering, sorting, search, and pagination.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | `1` | Page number (>= 1) |
| `page_size` | int | `25` | Results per page (1–100) |
| `status` | string | — | Filter by `DocumentStatusEnum` |
| `file_type` | string | — | Filter by `FileTypeEnum` |
| `document_type` | string | — | Filter by `DocumentTypeEnum` |
| `tags` | string | — | Comma-separated tags (AND logic) |
| `sort_by` | string | `created_at` | Sort field |
| `sort_order` | string | `desc` | `asc` or `desc` |
| `search` | string | — | Substring search on `original_file_name` |
| `date_from` | string | — | ISO date (inclusive) |
| `date_to` | string | — | ISO date (inclusive) |

```http
GET http://localhost:8000/api/v1/documents?status=parsed&file_type=pdf&page=1&page_size=10
```

**Response** `200`:
```json
{
    "documents": [{ "id": "...", "file_name": "...", "status": "parsed", ... }],
    "total": 42,
    "page": 1,
    "page_size": 10
}
```

---

#### `POST /api/v1/documents/ingest`

Ingest files from local filesystem paths.

**Request body**:
```json
{
    "source": "path/to/file/or/folder",
    "storage_mode": "managed",
    "tags": ["optional", "tags"],
    "recursive": true
}
```

> **[DEVIATION D9]**: `source` also accepts a list of paths: `["path1", "path2"]`.

```http
POST http://localhost:8000/api/v1/documents/ingest
Content-Type: application/json

{
    "source": "/path/to/file.pdf",
    "storage_mode": "managed",
    "tags": ["test"]
}
```

**Response** `200`:
```json
{
    "documents": [{ "id": "...", "file_name": "...", "status": "new" }],
    "skipped": [{ "path": "...", "reason": "unsupported_format" }]
}
```

---

#### `POST /api/v1/documents/upload` **[DEVIATION D2]**

Upload files via multipart form data. Saves to `DATA_FOLDER/uploads/`, then ingests.

| Form field | Type | Default | Description |
|------------|------|---------|-------------|
| `files` | file(s) | **required** | One or more files |
| `tags` | string | `""` | Comma-separated tags |
| `storage_mode` | string | `managed` | `managed` or `external` |
| `parse_after_upload` | bool | `false` | Auto-parse after ingest |

```http
POST http://localhost:8000/api/v1/documents/upload
Content-Type: multipart/form-data; boundary=----Boundary

------Boundary
Content-Disposition: form-data; name="files"; filename="report.pdf"
Content-Type: application/pdf

< ./report.pdf
------Boundary
Content-Disposition: form-data; name="tags"

important,review
------Boundary
Content-Disposition: form-data; name="storage_mode"

managed
------Boundary
Content-Disposition: form-data; name="parse_after_upload"

true
------Boundary--
```

**Response** `200`: Same as ingest response.

---

#### `POST /api/v1/documents/{document_id}/parse`

Parse a single document.

```http
POST http://localhost:8000/api/v1/documents/{{document_id}}/parse
Content-Type: application/json

{}
```

With config override:
```http
POST http://localhost:8000/api/v1/documents/{{document_id}}/parse
Content-Type: application/json

{
    "parser_config_override": {}
}
```

**Response** `200`:
```json
{
    "document_id": "...",
    "status": "parsed",
    "page_count": 5,
    "element_count": 42
}
```

**Errors**: `404 DOCUMENT_NOT_FOUND`, `409 DOCUMENT_LOCKED`

---

#### `POST /api/v1/documents/parse`

Batch parse documents by IDs, tags, or status filter.

```http
POST http://localhost:8000/api/v1/documents/parse
Content-Type: application/json

{
    "document_ids": ["id1", "id2"]
}
```

```http
POST http://localhost:8000/api/v1/documents/parse
Content-Type: application/json

{
    "tags": ["bill"]
}
```

```http
POST http://localhost:8000/api/v1/documents/parse
Content-Type: application/json

{
    "status_filter": "new"
}
```

**Response** `200`:
```json
{ "queued": 10, "skipped": 2 }
```

---

#### `GET /api/v1/documents/{document_id}`

Get full document model.

```http
GET http://localhost:8000/api/v1/documents/{{document_id}}
```

**Response** `200`: Full document JSON.

**Errors**: `404 DOCUMENT_NOT_FOUND`

---

#### `GET /api/v1/documents/{document_id}/file` **[DEVIATION D3]**

Download the raw file (PDF, image, etc.) as a binary response.

```http
GET http://localhost:8000/api/v1/documents/{{document_id}}/file
```

**Response** `200`: Binary file with appropriate `Content-Type`.

**Errors**: `404 DOCUMENT_NOT_FOUND`, `404 FILE_NOT_FOUND` **[DEVIATION D11]**

---

#### `GET /api/v1/documents/{document_id}/pages`

Get all pages for a document.

```http
GET http://localhost:8000/api/v1/documents/{{document_id}}/pages
```

**Response** `200`: Array of page objects.

**Errors**: `404 DOCUMENT_NOT_FOUND`

---

#### `GET /api/v1/documents/{document_id}/pages/{page_number}`

Get a specific page.

```http
GET http://localhost:8000/api/v1/documents/{{document_id}}/pages/1
```

**Response** `200`: Page object.

**Errors**: `404 DOCUMENT_NOT_FOUND`

---

#### `GET /api/v1/documents/{document_id}/pages/{page_number}/thumbnail`

Get a JPEG thumbnail of a specific page. Useful for document previews in the UI.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `width` | int | `300` | Thumbnail width in pixels (16–2048) |

```http
GET http://localhost:8000/api/v1/documents/{{document_id}}/pages/1/thumbnail?width=300
```

**Response** `200`: Binary JPEG image (`Content-Type: image/jpeg`).

**Response** `307`: Redirect to Azure Blob SAS URL (same pattern as `/file` endpoint — when storage backend is Azure Blob, returns a `307 Temporary Redirect` with a time-limited SAS URL instead of streaming the bytes through the API server).

**Headers**: `Cache-Control: max-age=3600`

**Errors**: `404 DOCUMENT_NOT_FOUND`, `400 INVALID_REQUEST` (unsupported file type)

**Implementation notes**:
- Uses `pymupdf` (`fitz`) for PDF page rasterization and image resizing (lazy import to avoid loading pymupdf for non-thumbnail routes)
- Thumbnails cached in storage backend using naming convention `{doc_id}.p{N}.thumb.jpg` (local: `data/managed/`, Azure: `az://managed/`)
- Cache check via `storage.list_files(prefix=...)` before generation — if a cached thumbnail exists, it is served directly
- Same SAS redirect pattern as the `/file` endpoint for Azure Blob storage

---

#### `POST /api/v1/documents/{document_id}/tags`

Add tags to a document (uses `$addToSet`; no duplicates).

```http
POST http://localhost:8000/api/v1/documents/{{document_id}}/tags
Content-Type: application/json

{
    "tags": ["important", "review"]
}
```

**Response** `200`: Updated document JSON.

**Errors**: `404 DOCUMENT_NOT_FOUND`

---

#### `DELETE /api/v1/documents/{document_id}/tags/{tag}`

Remove a single tag from a document.

```http
DELETE http://localhost:8000/api/v1/documents/{{document_id}}/tags/review
```

**Response** `200`: Updated document JSON.

**Errors**: `404 DOCUMENT_NOT_FOUND`

---

#### `DELETE /api/v1/documents/{document_id}` **[DEVIATION D4]**

Delete a document, its pages, and its managed file (if any).

```http
DELETE http://localhost:8000/api/v1/documents/{{document_id}}
```

**Response** `204`: No content.

**Errors**: `404 DOCUMENT_NOT_FOUND`

---

### Search

#### `POST /api/v1/search/` **[DEVIATION D14]**

Unified search across pages or documents using full-text, vector, or hybrid search.

**Minimal request**:
```http
POST http://localhost:8000/api/v1/search/
Content-Type: application/json

{
    "query": "search terms",
    "top_k": 5
}
```

**Full request body reference**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string | **required** | Search query text |
| `search_target` | enum | `"pages"` | `"pages"` or `"documents"` |
| `search_mode` | enum | `"hybrid"` | `"fulltext"`, `"vector"`, or `"hybrid"` |
| `fulltext.enabled` | bool | `true` | Enable full-text search |
| `fulltext.content_field` | string | `"content"` | `"content"` or `"content_markdown"` |
| `fulltext.fuzzy.enabled` | bool | `false` | Enable fuzzy matching |
| `fulltext.fuzzy.max_edits` | int | `2` | Max Levenshtein edits (1–2) |
| `fulltext.fuzzy.prefix_length` | int | `3` | Exact-match prefix length |
| `fulltext.score_boost` | float | `1.0` | Score multiplier in hybrid mode |
| `vector.enabled` | bool | `true` | Enable vector search |
| `vector.index_name` | string | `null` | Atlas index name (auto-selected if null) |
| `vector.embedding_model` | string | `null` | litellm model ID (inferred if null) |
| `vector.num_candidates` | int | `100` | Candidate vectors to consider |
| `vector.score_boost` | float | `1.0` | Score multiplier in hybrid mode |
| `hybrid.combination_method` | enum | `"rrf"` | `"rrf"` or `"weighted_sum"` |
| `hybrid.rrf_k` | int | `60` | RRF smoothing constant |
| `hybrid.weights.fulltext` | float | `0.5` | Full-text weight (weighted_sum only) |
| `hybrid.weights.vector` | float | `0.5` | Vector weight (weighted_sum only) |
| `filters.tags` | list[str] | `null` | Filter by tags (AND) |
| `filters.file_type` | string | `null` | Filter by file type |
| `filters.document_ids` | list[str] | `null` | Restrict to document IDs |
| `filters.status` | string | `null` | Filter by status |
| `filters.document_type` | string | `null` | Filter by document type |
| `top_k` | int | `10` | Max results |
| `min_score` | float | `0.0` | Min combined score |
| `include_content_fields` | list[str] | `["content"]` | Content fields to return |

**Response** `200`:
```json
{
    "results": [
        {
            "id": "page_or_document_id",
            "document_id": "parent_document_id",
            "page_number": 3,
            "score": 0.87,
            "scores": { "fulltext": 0.82, "vector": 0.91 },
            "content": "matched content text...",
            "content_markdown": null,
            "file_name": "report.pdf",
            "tags": ["tag1"]
        }
    ],
    "total": 42,
    "search_target": "pages",
    "search_mode": "hybrid",
    "vector_index_used": "vec_pages_large_dot",
    "embedding_model_used": "text-embedding-3-large"
}
```

---

#### `GET /api/v1/search/indices`

List available vector search indices.

```http
GET http://localhost:8000/api/v1/search/indices
```

**Response** `200`:
```json
{
    "pages": [
        {
            "index_name": "vec_pages_large_dot",
            "embedding_model": "text-embedding-3-large",
            "field": "emb_content_markdown_text_embedding_3_large",
            "dimensions": 3072,
            "similarity": "dotProduct"
        }
    ],
    "documents": [...]
}
```

---

### Cases

#### `GET /api/v1/cases`

List cases with optional search and pagination.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | `1` | Page number |
| `page_size` | int | `25` | Results per page (1–100) |
| `search` | string | — | Substring search on case name |

```http
GET http://localhost:8000/api/v1/cases?search=test&page=1&page_size=10
```

**Response** `200`:
```json
{
    "cases": [{ "id": "...", "name": "...", "description": "...", "document_ids": [], ... }],
    "total": 5,
    "page": 1,
    "page_size": 10
}
```

---

#### `POST /api/v1/cases`

Create a new case.

```http
POST http://localhost:8000/api/v1/cases
Content-Type: application/json

{
    "name": "Case Name",
    "description": "Optional description"
}
```

**Response** `200`: Full case model.

---

#### `GET /api/v1/cases/{case_id}`

```http
GET http://localhost:8000/api/v1/cases/{{case_id}}
```

**Response** `200`: Full case model.

**Errors**: `404 CASE_NOT_FOUND` **[DEVIATION D10]**

---

#### `PUT /api/v1/cases/{case_id}`

Update case name and/or description.

```http
PUT http://localhost:8000/api/v1/cases/{{case_id}}
Content-Type: application/json

{
    "name": "Updated Name",
    "description": "Updated description"
}
```

**Response** `200`: Updated case model.

**Errors**: `404 CASE_NOT_FOUND`

---

#### `DELETE /api/v1/cases/{case_id}`

```http
DELETE http://localhost:8000/api/v1/cases/{{case_id}}
```

**Response** `204`: No content.

**Errors**: `404 CASE_NOT_FOUND`

---

#### `POST /api/v1/cases/{case_id}/documents`

Add documents to a case (uses `$addToSet`; no duplicates).

```http
POST http://localhost:8000/api/v1/cases/{{case_id}}/documents
Content-Type: application/json

{
    "document_ids": ["doc_id_1", "doc_id_2"]
}
```

**Response** `200`: Updated case model.

**Errors**: `404 CASE_NOT_FOUND`

---

#### `DELETE /api/v1/cases/{case_id}/documents/{document_id}`

Remove a document from a case.

```http
DELETE http://localhost:8000/api/v1/cases/{{case_id}}/documents/{{document_id}}
```

**Response** `200`: Updated case model.

**Errors**: `404 CASE_NOT_FOUND`

---

#### `GET /api/v1/cases/{case_id}/documents`

List documents in a case with pagination.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | `1` | Page number |
| `page_size` | int | `25` | Results per page (1–100) |

```http
GET http://localhost:8000/api/v1/cases/{{case_id}}/documents?page=1&page_size=10
```

**Response** `200`:
```json
{
    "documents": [{ ... }],
    "total": 10,
    "page": 1,
    "page_size": 10
}
```

**Errors**: `404 CASE_NOT_FOUND`

---

### Extraction

Extraction endpoints for field extraction, stored results, and split-classify.

#### `POST /api/v1/extract`

Extract fields from documents using LLM-based extraction.

**Request body**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `case_id` | string | `null` | Case ID for context |
| `case_type` | string | `"generic"` | Case type for prompt selection |
| `document_type` | string | **required** | Document type for field/prompt config |
| `extraction_mode` | enum | `"referenced"` | `"referenced"` or `"direct"` |
| `output_schema` | string | `null` | Output schema name |
| `infer_references` | bool | `false` | Run reference inference pass |
| `document_ids` | list[str] | `null` | Documents to extract from |
| `page_ids` | list[str] | `null` | Specific pages to extract from |
| `file_ids` | list[str] | `null` | Files to extract from |
| `fields` | list[str] | `null` | Specific fields to extract |
| `field_overrides` | list[FieldDefinition] | `null` | Override field definitions |
| `reference_granularity` | enum | `"full"` | `"full"`, `"page"`, or `"none"` |
| `content_mode` | enum | `"markdown"` | `"markdown"` or `"html"` |

```http
POST http://localhost:8000/api/v1/extract
Content-Type: application/json

{
    "document_type": "invoice",
    "document_ids": ["{{document_id}}"],
    "case_type": "generic"
}
```

**Response** `200`:
```json
{
    "document_id": "...",
    "document_type": "invoice",
    "case_type": "generic",
    "extraction_mode": "referenced",
    "results": { "field_name": { "content": "...", "justification": "...", ... } },
    "reference_annotations": null,
    "model_used": "gpt-4.1",
    "reference_granularity": "full"
}
```

---

#### `GET /api/v1/field-results`

Get stored extraction results for a document.

| Parameter | Type | Description |
|-----------|------|-------------|
| `document_id` | string | **required** — Document ID |

```http
GET http://localhost:8000/api/v1/field-results?document_id={{document_id}}
```

**Response** `200`: Array of `FieldResultRecord` objects.

---

#### `POST /api/v1/split-classify`

Split a multi-document file into typed segments.

Requires exactly one `document_id` in the `document_ids` list.

```http
POST http://localhost:8000/api/v1/split-classify
Content-Type: application/json

{
    "document_type": "generic",
    "document_ids": ["{{document_id}}"],
    "case_type": "generic"
}
```

**Response** `200`:
```json
{
    "segments": [
        { "document_type": "invoice", "page_numbers": [1, 2, 3] },
        { "document_type": "receipt", "page_numbers": [4, 5] }
    ]
}
```

---

### Sync

Storage-to-DB synchronization endpoints. See [sync spec](specs/sync.md) for the full algorithm.

Sync request/response models are defined inline in `mydocs/backend/routes/sync.py`.
Core sync logic is in `mydocs/sync/` (scanner, reconciler, sidecar).

#### `POST /api/v1/sync/plan`

Build a sync plan by scanning managed storage and comparing with the database.

**Request body**:
```json
{
    "scan_path": "data/managed/",
    "verify_content": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `scan_path` | string | `null` | Override managed storage path (default: `DATA_FOLDER/managed/`) |
| `verify_content` | bool | `false` | Verify file content via SHA256 comparison |

```http
POST http://localhost:8000/api/v1/sync/plan
Content-Type: application/json

{}
```

**Response** `200`:
```json
{
    "items": [
        {
            "file_path": "/path/to/managed/abc123.pdf",
            "doc_id": "abc123",
            "action": "restore",
            "reason": "File and sidecar on disk, no DB record",
            "sidecar_path": "/path/to/managed/abc123.metadata.json"
        }
    ],
    "summary": { "restore": 2, "verified": 3 },
    "scan_path": "data/managed/",
    "scanned_at": "2026-02-18T17:00:00"
}
```

Actions: `restore`, `reparse`, `orphaned_db`, `verified`, `sidecar_missing`.

---

#### `POST /api/v1/sync/execute`

Execute a sync plan (scan + execute in one call).

**Request body**:
```json
{
    "scan_path": "data/managed/",
    "verify_content": false,
    "reparse": false,
    "actions": ["restore", "sidecar_missing"]
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `scan_path` | string | `null` | Override managed storage path |
| `verify_content` | bool | `false` | Verify file content via SHA256 |
| `reparse` | bool | `false` | Re-parse restored documents from `.di.json` cache |
| `actions` | list[str] | `null` | Filter to specific action types (default: all) |

```http
POST http://localhost:8000/api/v1/sync/execute
Content-Type: application/json

{
    "reparse": true
}
```

**Response** `200`:
```json
{
    "items": [
        {
            "item": { "doc_id": "abc123", "action": "restore", ... },
            "success": true,
            "error": null
        }
    ],
    "summary": { "restore": { "success": 2, "failed": 0 } },
    "started_at": "2026-02-18T17:00:00",
    "completed_at": "2026-02-18T17:00:12"
}
```

---

#### `POST /api/v1/sync/write-sidecars`

Write missing metadata sidecars for managed files that have DB records but no sidecar on disk.

**Request body**:
```json
{
    "scan_path": "data/managed/"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `scan_path` | string | `null` | Override managed storage path |

```http
POST http://localhost:8000/api/v1/sync/write-sidecars
Content-Type: application/json

{}
```

**Response** `200`:
```json
{
    "written": 5,
    "skipped": 0
}
```

---

#### `POST /api/v1/sync/migrate/plan`

Build a migration plan for cross-backend document migration (read-only).

**Request body**:
```json
{
    "source_backend": "local",
    "target_backend": "azure_blob"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `source_backend` | string | **required** — Source storage backend (`local` or `azure_blob`) |
| `target_backend` | string | **required** — Target storage backend (`local` or `azure_blob`) |

```http
POST http://localhost:8000/api/v1/sync/migrate/plan
Content-Type: application/json

{
    "source_backend": "local",
    "target_backend": "azure_blob"
}
```

**Response** `200`:
```json
{
    "items": [
        {
            "doc_id": "abc123",
            "file_name": "abc123.pdf",
            "source_path": "/data/managed/abc123.pdf",
            "storage_mode": "managed",
            "action": "copy",
            "reason": "Copy file + sidecar from local to azure_blob"
        }
    ],
    "summary": { "copy": 3, "copy_sidecar": 1, "skip_target": 2 },
    "source_backend": "local",
    "target_backend": "azure_blob",
    "planned_at": "2026-02-19T10:00:00"
}
```

---

#### `POST /api/v1/sync/migrate/execute`

Execute a cross-backend migration. This is a **storage-only** operation — no database writes. After migration, rebuild DB via `POST /api/v1/sync/execute`.

**Request body**:
```json
{
    "source_backend": "local",
    "target_backend": "azure_blob",
    "delete_source": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `source_backend` | string | — | **required** — Source storage backend |
| `target_backend` | string | — | **required** — Target storage backend |
| `delete_source` | bool | `false` | Delete source files after successful copy |

```http
POST http://localhost:8000/api/v1/sync/migrate/execute
Content-Type: application/json

{
    "source_backend": "local",
    "target_backend": "azure_blob"
}
```

**Response** `200`:
```json
{
    "items": [
        {
            "item": { "doc_id": "abc123", "action": "copy", ... },
            "success": true,
            "dest_path": "az://container/abc123.pdf",
            "error": null
        }
    ],
    "summary": { "copy": { "success": 3, "failed": 0 } },
    "source_backend": "local",
    "target_backend": "azure_blob",
    "started_at": "2026-02-19T10:00:00",
    "completed_at": "2026-02-19T10:00:15",
    "delete_source": false
}
```

---

## Error Handling

All errors use a consistent JSON format:

```json
{
    "detail": "Human-readable error message",
    "error_code": "DOCUMENT_NOT_FOUND",
    "status_code": 404
}
```

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `INVALID_REQUEST` | Malformed request body or parameters |
| 404 | `DOCUMENT_NOT_FOUND` | Document or page not found |
| 404 | `CASE_NOT_FOUND` | Case not found **[DEVIATION D10]** |
| 404 | `FILE_NOT_FOUND` | Raw file not found on disk **[DEVIATION D11]** |
| 409 | `DOCUMENT_LOCKED` | Document is currently being parsed |
| 422 | `VALIDATION_ERROR` | Request validation failed |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

Note: Extraction endpoints (`/extract`, `/field-results`, `/split-classify`) and sync endpoints use FastAPI's `HTTPException` directly, returning `{"detail": "..."}` without `error_code`/`status_code` fields.

---

## Package Structure (Actual)

```
mydocs/
  backend/
    __init__.py
    app.py                      # FastAPI application factory
    dependencies.py             # Pydantic request/response models
    routes/
      __init__.py
      documents.py              # Ingest, upload, parse, get, tags, delete endpoints
      search.py                 # Search and index listing endpoints
      cases.py                  # Case CRUD and document assignment endpoints
      extract.py                # Extraction, field-results, split-classify endpoints
      sync.py                   # Sync plan, execute, write-sidecars endpoints
```
