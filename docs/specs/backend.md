# Backend Specification

**Package**: `mydocs.backend`
**Version**: 1.0
**Status**: Draft

**Related Specs**: [parsing-engine.md](parsing-engine.md) (data models, pipeline), [retrieval-engine.md](retrieval-engine.md) (search), [extracting-engine.md](extracting-engine.md) (extraction), [cli.md](cli.md) (CLI interface)

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

*Required when Azure DI parser is used.

---

## 3. API Contracts

### 3.0 Health Check

```
GET /health
Response: { "status": "ok" }
```

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

### 3.12 Cases

Cases group related documents for review or investigation. The `Case` model is defined in `mydocs/models.py`.

The `Case` model includes a `type` field (string, default `"generic"`) for categorizing cases.

#### 3.12.1 List Cases
```
GET /api/v1/cases?page=1&page_size=25&search=term
Response: {
    "cases": [{ "id": "...", "name": "...", "description": "...", "document_ids": [...], "created_at": "...", "modified_at": "..." }],
    "total": 42,
    "page": 1,
    "page_size": 25
}
```

#### 3.9.2 Create Case
```
POST /api/v1/cases
Body: { "name": "Case Name", "description": "Optional description" }
Response: { ... full case model ... }
```

#### 3.9.3 Get Case
```
GET /api/v1/cases/{case_id}
Response: { ... full case model ... }
```

#### 3.9.4 Update Case
```
PUT /api/v1/cases/{case_id}
Body: { "name": "Updated Name", "description": "Updated description" }
Response: { ... full case model ... }
```

#### 3.9.5 Delete Case
```
DELETE /api/v1/cases/{case_id}
Response: 204 No Content
```

#### 3.9.6 Add Documents to Case
```
POST /api/v1/cases/{case_id}/documents
Body: { "document_ids": ["doc_id_1", "doc_id_2"] }
Response: { ... full case model ... }
```

#### 3.9.7 Remove Document from Case
```
DELETE /api/v1/cases/{case_id}/documents/{document_id}
Response: { ... full case model ... }
```

#### 3.9.8 List Documents in Case
```
GET /api/v1/cases/{case_id}/documents?page=1&page_size=25
Response: {
    "documents": [{ ... document model ... }],
    "total": 10,
    "page": 1,
    "page_size": 25
}
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
    routes/
      __init__.py
      documents.py              # Ingest, parse, get, tags endpoints
      search.py                 # Search and index listing endpoints
      cases.py                  # Case CRUD and document assignment endpoints
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
