# Backend Specification

**Package**: `mydocs.backend`
**Version**: 1.0
**Status**: Draft

**Related Specs**: [parsing-engine.md](parsing-engine.md) (data models, pipeline), [retrieval-engine.md](retrieval-engine.md) (search), [extracting-engine.md](extracting-engine.md) (extraction), [cli.md](cli.md) (CLI interface), [sync.md](sync.md) (storage-to-DB sync)

---

## 1. Overview

The backend is a FastAPI application that provides an HTTP API wrapping the parsing pipeline and retrieval engine. It serves as the primary interface for the Vue.js UI and external integrations.

---

## 2. Application Configuration

Environment-variable-based configuration for infrastructure settings:

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGO_URL` | Yes | MongoDB connection URL |
| `MONGO_USER` | Yes | MongoDB username |
| `MONGO_PASSWORD` | Yes | MongoDB password |
| `MONGO_DB_NAME` | Yes | MongoDB database name |
| `AZURE_DI_ENDPOINT` | Yes* | Azure DI endpoint URL |
| `AZURE_DI_API_KEY` | Yes* | Azure DI API key |
| `AZURE_OPENAI_API_KEY` | Yes | Azure OpenAI API key (read by litellm for `azure/` models) |
| `AZURE_OPENAI_API_BASE` | Yes | Azure OpenAI endpoint URL (read by litellm for `azure/` models) |
| `AZURE_OPENAI_API_VERSION` | No | Azure OpenAI API version (default: `2024-12-01-preview`) |
| `DATA_FOLDER` | No | Root data folder (default: `./data`) |
| `CONFIG_ROOT` | No | Root config folder (default: `./config`) |
| `SERVICE_NAME` | No | Service identifier (default: `mydocs`) |
| `LOG_LEVEL` | No | Logging level (default: `INFO`, used by tinystructlog) |
| `ENTRA_TENANT_ID` | No | Azure AD tenant ID. When empty, authentication is disabled (local dev mode). |
| `ENTRA_CLIENT_ID` | No** | Entra ID app registration client ID. Required when `ENTRA_TENANT_ID` is set. |
| `ENTRA_ISSUER` | No | Token issuer URL (default: `https://login.microsoftonline.com/{ENTRA_TENANT_ID}/v2.0`). |

*Required when Azure DI parser is used.
**Required when `ENTRA_TENANT_ID` is set.

---

## 3. API Contracts

### 3.0 Health Check

```
GET /health
Response: { "status": "ok" }
```

The health endpoint is **unauthenticated** -- it is excluded from the global auth dependency so Kubernetes liveness/readiness probes work without tokens.

All other `/api/v1/*` endpoints require a valid Bearer token when authentication is enabled (see Section 8).

### 3.1 Ingest Files
```
POST /api/v1/documents/ingest
Body: {
    "source": "path/to/file/or/folder" | ["path1", "path2"],
    "storage_mode": "managed" | "external",
    "tags": ["optional", "tags"],
    "recursive": true
}
Response: {
    "documents": [{ "id": "...", "file_name": "...", "status": "new" }],
    "skipped": [{ "path": "...", "reason": "unsupported_format" }]
}
```

The `source` field accepts either a single path (string) or a list of paths.

### 3.1.1 Upload Files

Upload files via multipart form data. Files are saved to `DATA_FOLDER/uploads/` then ingested.

**Note**: Uploaded files always use **managed** storage mode (the file is copied into managed storage). External mode is only available via the `/ingest` endpoint for path-based ingestion.

```
POST /api/v1/documents/upload
Content-Type: multipart/form-data

Form fields:
    files:              (required) One or more files
    tags:               (optional) Comma-separated tags, default ""
    parse_after_upload:  (optional) true | false, default false

Response: {
    "documents": [{ "id": "...", "file_name": "...", "status": "new" }],
    "skipped": [{ "path": "...", "reason": "unsupported_format" }]
}
```

When `parse_after_upload` is `true`, a batch parse is triggered for all ingested documents.

### 3.2 Parse Documents
```
POST /api/v1/documents/{document_id}/parse
Body: {
    "parser_config_override": { ... }    # Optional config overrides
}
Response: {
    "document_id": "...",
    "status": "parsed",
    "page_count": 5,
    "element_count": 42
}
```

### 3.3 Batch Parse
```
POST /api/v1/documents/parse
Body: {
    "document_ids": ["id1", "id2"],       # Optional: specific documents
    "tags": ["tag1"],                       # Optional: parse all with these tags
    "status_filter": "new"                  # Optional: parse only with this status
}
Response: {
    "queued": 10,
    "skipped": 2
}
```

### 3.4 Search

A unified search endpoint that supports searching across **pages** or **documents**, using full-text search, vector search, or a hybrid of both. See [retrieval-engine.md](retrieval-engine.md) for the internal search models and behavior.

```
POST /api/v1/search
```

#### 3.4.1 Request Body

```json
{
    "query": "search terms",
    "search_target": "pages",
    "search_mode": "hybrid",

    "fulltext": {
        "enabled": true,
        "content_field": "content",
        "fuzzy": {
            "enabled": false,
            "max_edits": 2,
            "prefix_length": 3
        },
        "score_boost": 1.0
    },

    "vector": {
        "enabled": true,
        "index_name": "vec_pages_large_dot",
        "embedding_model": "text-embedding-3-large",
        "num_candidates": 100,
        "score_boost": 1.0
    },

    "hybrid": {
        "combination_method": "rrf",
        "rrf_k": 60,
        "weights": {
            "fulltext": 0.5,
            "vector": 0.5
        }
    },

    "filters": {
        "tags": ["tag1"],
        "file_type": "pdf",
        "document_ids": ["id1", "id2"],
        "status": "parsed",
        "document_type": "generic"
    },

    "top_k": 10,
    "min_score": 0.0,
    "include_content_fields": ["content", "content_markdown"]
}
```

#### 3.4.2 Field Reference

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | string | **required** | Search query text (used for both full-text and vector search) |
| `search_target` | enum | `"pages"` | What to search: `"pages"` or `"documents"` |
| `search_mode` | enum | `"hybrid"` | Search strategy: `"fulltext"`, `"vector"`, or `"hybrid"` |

**Full-Text Search Parameters** (`fulltext`):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `fulltext.enabled` | bool | `true` | Whether full-text search is active (auto-set by `search_mode`) |
| `fulltext.content_field` | string | `"content"` | Field to search: `"content"` (plain text) or `"content_markdown"` |
| `fulltext.fuzzy.enabled` | bool | `false` | Enable fuzzy matching for typo tolerance |
| `fulltext.fuzzy.max_edits` | int | `2` | Max Levenshtein edits for fuzzy matching (1-2) |
| `fulltext.fuzzy.prefix_length` | int | `3` | Number of prefix characters that must match exactly |
| `fulltext.score_boost` | float | `1.0` | Multiplier for full-text scores in hybrid mode |

**Vector Search Parameters** (`vector`):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `vector.enabled` | bool | `true` | Whether vector search is active (auto-set by `search_mode`) |
| `vector.index_name` | string | `null` | Atlas Vector Search index name. If `null`, auto-selected from available indices based on `search_target` |
| `vector.embedding_model` | string | `null` | litellm model ID for query embedding. If `null`, inferred from the selected vector index configuration |
| `vector.num_candidates` | int | `100` | Number of candidate vectors to consider (higher = more accurate but slower) |
| `vector.score_boost` | float | `1.0` | Multiplier for vector scores in hybrid mode |

**Hybrid Search Parameters** (`hybrid`):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `hybrid.combination_method` | enum | `"rrf"` | How to combine results: `"rrf"` (Reciprocal Rank Fusion) or `"weighted_sum"` |
| `hybrid.rrf_k` | int | `60` | RRF smoothing constant (only used when `combination_method` = `"rrf"`) |
| `hybrid.weights.fulltext` | float | `0.5` | Weight for full-text scores (only used when `combination_method` = `"weighted_sum"`) |
| `hybrid.weights.vector` | float | `0.5` | Weight for vector scores (only used when `combination_method` = `"weighted_sum"`) |

**Filters** (`filters`):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `filters.tags` | list[str] | `null` | Filter by document tags (AND logic) |
| `filters.file_type` | string | `null` | Filter by `FileTypeEnum` value |
| `filters.document_ids` | list[str] | `null` | Restrict search to specific document IDs |
| `filters.status` | string | `null` | Filter by `DocumentStatusEnum` value |
| `filters.document_type` | string | `null` | Filter by `DocumentTypeEnum` value |

**Result Control**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `top_k` | int | `10` | Maximum number of results to return |
| `min_score` | float | `0.0` | Minimum combined score threshold for results |
| `include_content_fields` | list[str] | `["content"]` | Which content fields to return in results (e.g., `"content"`, `"content_markdown"`, `"content_html"`) |

#### 3.4.3 Response

```json
{
    "results": [
        {
            "id": "page_or_document_id",
            "document_id": "parent_document_id",
            "page_number": 3,
            "score": 0.87,
            "scores": {
                "fulltext": 0.82,
                "vector": 0.91
            },
            "content": "matched content text...",
            "content_markdown": "[p0] matched content...",
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

### 3.5 List Vector Indices

```
GET /api/v1/search/indices
Response: {
    "pages": [
        {
            "index_name": "vec_pages_large_dot",
            "embedding_model": "text-embedding-3-large",
            "field": "emb_content_markdown_text_embedding_3_large",
            "dimensions": 3072,
            "similarity": "dotProduct"
        }
    ],
    "documents": [
        {
            "index_name": "vec_documents_large_dot",
            "embedding_model": "text-embedding-3-large",
            "field": "emb_content_text_embedding_3_large",
            "dimensions": 3072,
            "similarity": "dotProduct"
        }
    ]
}
```

### 3.6 List Documents

```
GET /api/v1/documents?page=1&page_size=25
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | `1` | Page number (>= 1) |
| `page_size` | int | `25` | Results per page (1–100) |
| `status` | string | `null` | Filter by `DocumentStatusEnum` value |
| `file_type` | string | `null` | Filter by `FileTypeEnum` value |
| `document_type` | string | `null` | Filter by `DocumentTypeEnum` value |
| `tags` | string | `null` | Comma-separated tags (AND logic) |
| `sort_by` | string | `"created_at"` | Field to sort by |
| `sort_order` | string | `"desc"` | Sort direction: `"asc"` or `"desc"` |
| `search` | string | `null` | Substring search on `original_file_name` (case-insensitive) |
| `date_from` | string | `null` | ISO date string, inclusive lower bound on `created_at` |
| `date_to` | string | `null` | ISO date string, inclusive upper bound on `created_at` |

```
Response: {
    "documents": [{ ... document model ... }],
    "total": 42,
    "page": 1,
    "page_size": 25
}
```

### 3.7 Get Document
```
GET /api/v1/documents/{document_id}
Response: { ... full document model ... }
```

### 3.8 Get Document File

Download the raw file (PDF, image, etc.) as a binary response with the appropriate `Content-Type`.

```
GET /api/v1/documents/{document_id}/file
Response: Binary file content
```

Returns `404 FILE_NOT_FOUND` if the file is not present on disk.

### 3.8.1 Get Document Thumbnail

Returns a PNG thumbnail of the document's first page. Thumbnails are generated using PyMuPDF and cached in the storage backend alongside the document file as `{doc_id}.thumb.png`.

```
GET /api/v1/documents/{document_id}/thumbnail
Query Parameters:
    width:   (optional) Max width in pixels, default 300
Response: image/png binary content
```

**Behavior:**
- If a cached thumbnail exists in managed storage, it is served directly.
- If no cached thumbnail exists, the backend generates one on-the-fly using PyMuPDF (`fitz`), caches it via `write_managed_bytes()`, and returns it.
- For non-PDF files (images), the original file is resized to thumbnail dimensions.
- For unsupported file types (DOCX, XLSX, etc.), returns a `204 No Content` response and the UI shows a placeholder icon.
- Returns `404 FILE_NOT_FOUND` if the document or its file is not found.
- For Azure Blob storage: the cached thumbnail is stored in the blob container and served via SAS URL redirect (same pattern as file download).

**Cache invalidation:** Thumbnails are regenerated when a document is re-parsed (the parse endpoint deletes the cached thumbnail before parsing).

### 3.8.2 Get Page Image

Returns a rendered PNG image of a specific document page. Uses PyMuPDF to render the page at the requested resolution.

```
GET /api/v1/documents/{document_id}/pages/{page_number}/image
Query Parameters:
    width:   (optional) Max width in pixels, default 800
    dpi:     (optional) Render DPI, default 150
Response: image/png binary content
```

**Behavior:**
- Renders the specified page of the document using PyMuPDF at the requested DPI.
- Images are **not cached** by default (they are generated on each request). Future optimization may add caching for commonly accessed pages.
- For image-type documents (JPEG, PNG, etc.), returns the original image (optionally resized).
- Returns `404 FILE_NOT_FOUND` if the document file is not found.
- Returns `404` if the `page_number` exceeds the document's total page count.

### 3.9 Get Pages
```
GET /api/v1/documents/{document_id}/pages
GET /api/v1/documents/{document_id}/pages/{page_number}
```

### 3.10 Manage Tags
```
POST /api/v1/documents/{document_id}/tags
Body: { "tags": ["new_tag"] }

DELETE /api/v1/documents/{document_id}/tags/{tag}
```

### 3.11 Delete Document

Deletes a document, all its pages, and the managed file (if any) from disk.

```
DELETE /api/v1/documents/{document_id}
Response: 204 No Content
```

### 3.12 Extract Fields

```
POST /api/v1/extract
Body: ExtractionRequest (see extracting-engine.md Section 2.5)
Response: ExtractionResponse (see extracting-engine.md Section 2.6)
```

### 3.13 Get Field Results

```
GET /api/v1/field-results?document_id={document_id}
Response: list[FieldResultRecord]
```

### 3.14 Split and Classify

Split a multi-document file into typed segments using LLM classification. Requires exactly one `document_id`.

```
POST /api/v1/split-classify
Body: {
    "document_type": "generic",
    "document_ids": ["document_id"],
    "case_type": "generic",
    "content_mode": "markdown"
}
Response: {
    "segments": [
        { "document_type": "invoice", "page_numbers": [1, 2, 3] },
        { "document_type": "receipt", "page_numbers": [4, 5] }
    ],
    "subdocuments": [...]
}
```

The split-classify prompt is loaded from `config/extracting/{case_type}/split_classify/prompts/main.yaml`. If no prompt exists for the given `case_type`, a `ConfigNotFoundError` (500) is returned.

### 3.15 Cases

Cases group related documents for review or investigation. The `Case` model is defined in `mydocs/models.py`.

The `Case` model includes a `type` field (string, default `"generic"`) for categorizing cases.

#### 3.15.1 List Cases
```
GET /api/v1/cases?page=1&page_size=25&search=term
Response: {
    "cases": [{ "id": "...", "name": "...", "description": "...", "document_ids": [...], "created_at": "...", "modified_at": "..." }],
    "total": 42,
    "page": 1,
    "page_size": 25
}
```

#### 3.15.2 Create Case
```
POST /api/v1/cases
Body: { "name": "Case Name", "description": "Optional description" }
Response: { ... full case model ... }
```

#### 3.15.3 Get Case
```
GET /api/v1/cases/{case_id}
Response: { ... full case model ... }
```

#### 3.15.4 Update Case
```
PUT /api/v1/cases/{case_id}
Body: { "name": "Updated Name", "description": "Updated description" }
Response: { ... full case model ... }
```

#### 3.15.5 Delete Case
```
DELETE /api/v1/cases/{case_id}
Response: 204 No Content
```

#### 3.15.6 Add Documents to Case
```
POST /api/v1/cases/{case_id}/documents
Body: { "document_ids": ["doc_id_1", "doc_id_2"] }
Response: { ... full case model ... }
```

#### 3.15.7 Remove Document from Case
```
DELETE /api/v1/cases/{case_id}/documents/{document_id}
Response: { ... full case model ... }
```

#### 3.15.8 List Documents in Case
```
GET /api/v1/cases/{case_id}/documents?page=1&page_size=25
Response: {
    "documents": [{ ... document model ... }],
    "total": 10,
    "page": 1,
    "page_size": 25
}
```

### 3.16 Sync

Storage-to-DB synchronization endpoints. See [sync.md](sync.md) for the full sync specification.

#### 3.16.1 Build Sync Plan
```
POST /api/v1/sync/plan
Body: {
    "scan_path": "data/managed/",
    "verify_content": false
}
Response: { ... SyncPlan model ... }
```

#### 3.16.2 Execute Sync
```
POST /api/v1/sync/execute
Body: {
    "scan_path": "data/managed/",
    "verify_content": false,
    "reparse": false,
    "actions": ["restore", "sidecar_missing"]
}
Response: { ... SyncReport model ... }
```

#### 3.16.3 Write Sidecars
```
POST /api/v1/sync/write-sidecars
Body: {
    "scan_path": "data/managed/"
}
Response: {
    "written": 5,
    "skipped": 2
}
```

#### 3.16.4 Build Migrate Plan
```
POST /api/v1/sync/migrate/plan
Body: {
    "source_backend": "local",         // Required: source storage backend
    "target_backend": "azure_blob"     // Required: target storage backend
}
Response: { ... MigratePlan model ... }
```

#### 3.16.5 Execute Migrate
```
POST /api/v1/sync/migrate/execute
Body: {
    "source_backend": "local",         // Required: source storage backend
    "target_backend": "azure_blob",    // Required: target storage backend
    "delete_source": false             // Optional: delete source files after copy
}
Response: { ... MigrateReport model ... }
```

---

## 4. Database Architecture

The backend relies on the ODM layer and collection models defined in [parsing-engine.md](parsing-engine.md).

### 4.1 ODM Layer

Uses `lightodm` (Lightweight MongoDB ODM). See [parsing-engine.md](parsing-engine.md) Section 8 for details.

### 4.2 Collections

| Collection | Model | Description |
|------------|-------|-------------|
| `documents` | `Document` | Unified file + document records |
| `pages` | `DocumentPage` | Individual page content and embeddings |
| `cases` | `Case` | Document groupings for review/investigation |

### 4.3 Future Database Backends

| Backend | Priority | Notes |
|---------|----------|-------|
| **MongoDB** | P0 (initial) | Primary backend with Atlas Search and Vector Search |
| **PostgreSQL** | P2 (future) | With pgvector extension for vector search |
| **SQLite** | P3 (future) | For local/embedded deployments |

---

## 5. Error Handling

### 5.1 Standard Error Response

All API errors return a consistent JSON format:

```json
{
    "detail": "Human-readable error message",
    "error_code": "DOCUMENT_NOT_FOUND",
    "status_code": 404
}
```

### 5.2 Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 401 | `UNAUTHORIZED` | Missing, expired, or invalid Bearer token (see Section 8) |
| 400 | `INVALID_REQUEST` | Malformed request body or parameters |
| 404 | `DOCUMENT_NOT_FOUND` | Document ID does not exist |
| 409 | `DOCUMENT_LOCKED` | Document is currently being parsed |
| 422 | `VALIDATION_ERROR` | Request validation failed |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

---

## 6. Package Structure

```
mydocs/
  backend/
    __init__.py
    app.py                      # FastAPI application factory
    auth.py                     # Entra ID JWT validation (get_current_user dependency)
    routes/
      __init__.py
      documents.py              # Ingest, parse, get, tags endpoints
      search.py                 # Search and index listing endpoints
      cases.py                  # Case CRUD and document assignment endpoints
      extract.py                # Extraction, field-results, split-classify endpoints
      sync.py                   # Sync plan, execute, write-sidecars endpoints
    dependencies.py             # FastAPI dependency injection
```

---

## 7. Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `python-dotenv` | Environment variable loading |
| `lightodm` | MongoDB ODM (transitive) |
| `pydantic` | Request/response models (transitive via FastAPI) |
| `PyJWT[crypto]` | JWT decoding and RS256 signature validation (Entra ID auth) |
| `httpx` | Async HTTP client for fetching Entra ID JWKS keys |

---

## 8. Authentication & Authorization

### 8.1 Overview

API authentication uses **Microsoft Entra ID** (Azure AD) JWT bearer tokens. The implementation lives in `mydocs/backend/auth.py` and is wired into the application as a **global dependency** on all API routers via `Depends(get_current_user)`.

The `/health` endpoint is explicitly excluded from authentication so Kubernetes liveness and readiness probes work without tokens.

### 8.2 Token Validation Flow

1. Extract the `Authorization: Bearer <token>` header via FastAPI's `HTTPBearer` security scheme.
2. Decode the JWT header (unverified) to obtain the `kid` (key ID).
3. Fetch the signing keys from Microsoft's JWKS endpoint (`https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys`). Keys are cached in-memory; the cache is busted and retried once if the `kid` is not found (to handle key rotation).
4. Verify the JWT signature (RS256), audience (`ENTRA_CLIENT_ID`), issuer (`ENTRA_ISSUER`), and expiry.
5. Return the decoded claims as a `dict` to downstream route handlers.

### 8.3 Local Development Mode

When `ENTRA_TENANT_ID` is **unset or empty**, the `get_current_user` dependency skips all validation and returns a stub user:

```python
{"sub": "local-dev", "name": "Local Developer"}
```

This allows the entire application to run without any Entra ID configuration during local development.

### 8.4 Error Responses

| Condition | HTTP Status | Detail |
|-----------|-------------|--------|
| Missing `Authorization` header | 401 | `Missing authorization header` |
| Malformed token | 401 | `Invalid token header` |
| Signing key not found | 401 | `Unable to find signing key` |
| Expired token | 401 | `Token has expired` |
| Invalid signature/audience/issuer | 401 | `Token validation failed: <reason>` |
