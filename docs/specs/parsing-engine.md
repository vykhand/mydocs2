# Parsing Engine Specification

**Module**: `mydocs2.parsing`
**Version**: 1.0
**Status**: Draft

---

## 1. Overview

The parsing engine is responsible for ingesting files (initially PDFs), extracting structured content using document intelligence services (initially Azure Document Intelligence), and storing the results as queryable documents with full-text search and vector search capabilities.

The engine transforms raw files into a three-level hierarchy:

```
File -> Document -> DocumentPage
                 -> DocumentElement (embedded in Document)
```

Since in mydocs2 one file always corresponds to one document, the `File` and `Document` are stored in the same MongoDB collection (`documents`) as a unified model. Pages are stored separately in a `pages` collection for granular search and retrieval.

---

## 2. Ingestion Modes

### 2.1 Input Sources

Files can be ingested from the following sources:

| Source | Priority | Description |
|--------|----------|-------------|
| **Local Filesystem** | P0 (initial) | Files from a local directory path |
| **Azure Blob Storage** | P1 (future) | Files from Azure Blob containers |
| **AWS S3** | P2 (future) | Files from S3 buckets |
| **GCP Cloud Storage** | P2 (future) | Files from GCS buckets |
| **OneDrive** | P3 (future) | Files from OneDrive / SharePoint |

Ingestion accepts:
- A single file path/URI
- A list of file paths/URIs
- A folder path/URI (processed recursively, filtering for supported formats)

### 2.2 Supported File Formats

| Format | Priority | MIME Type |
|--------|----------|-----------|
| PDF | P0 (initial) | `application/pdf` |
| DOCX | P1 (future) | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| XLSX | P1 (future) | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| PPTX | P1 (future) | `application/vnd.openxmlformats-officedocument.presentationml.presentation` |
| JPEG/PNG/BMP/TIFF | P1 (future) | `image/*` |
| TXT | P2 (future) | `text/plain` |

### 2.3 Storage Modes

Files can be imported in two modes:

#### 2.3.1 Managed Mode
- The file is **copied** into managed storage
- The managed storage path is recorded in the document model
- Initial backend: local filesystem mapped to `./data/managed/`
- Future backends: Azure Blob Storage, S3, GCP Cloud Storage

#### 2.3.2 External Mode
- The file **remains at its original location**
- Only metadata is stored (as a sidecar JSON file: `<filename>.metadata.json` alongside the original file, and in the database)
- The original path/URI is recorded for access
- Useful for large file repositories where copying is impractical

### 2.4 Managed File Store Backends

| Backend | Priority | Description |
|---------|----------|-------------|
| **Local Filesystem** | P0 (initial) | Files stored under `./data/managed/` |
| **Azure Blob Storage** | P1 (future) | Azure Blob container |
| **AWS S3** | P2 (future) | S3 bucket |
| **GCP Cloud Storage** | P2 (future) | GCS bucket |

---

## 3. Data Models

### 3.1 Enumerations

#### 3.1.1 FileTypeEnum
Identifies the file format.

```
FileTypeEnum(StrEnum):
    UNKNOWN = "unknown"
    PDF = "pdf"
    TXT = "txt"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    JPEG = "jpeg"
    PNG = "png"
    BMP = "bmp"
    TIFF = "tiff"
```

#### 3.1.2 StorageModeEnum
Identifies how the file is stored.

```
StorageModeEnum(StrEnum):
    MANAGED = "managed"
    EXTERNAL = "external"
```

#### 3.1.3 StorageBackendEnum
Identifies the storage backend for managed files and file sources.

```
StorageBackendEnum(StrEnum):
    LOCAL = "local"
    AZURE_BLOB = "azure_blob"
    S3 = "s3"
    GCS = "gcs"
    ONEDRIVE = "onedrive"
```

#### 3.1.4 DocumentStatusEnum
Tracks the processing status of a document.

```
DocumentStatusEnum(StrEnum):
    NEW = "new"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_SUPPORTED = "not_supported"
```

#### 3.1.5 DocumentElementTypeEnum
Types of structural elements extracted from documents.

```
DocumentElementTypeEnum(StrEnum):
    PARAGRAPH = "paragraph"
    TABLE = "table"
    KEY_VALUE_PAIR = "key_value_pair"
    IMAGE = "image"
    BARCODE = "barcode"
```

#### 3.1.6 DocumentTypeEnum
Classification of the document (initially only GENERIC).

```
DocumentTypeEnum(StrEnum):
    GENERIC = "generic"
```

### 3.2 Embedded Models (not stored as separate collections)

#### 3.2.1 FileMetadata
Stores filesystem and format-specific metadata about the original file.

```
FileMetadata(BaseModel):
    size_bytes: Optional[int]           # File size in bytes
    mime_type: Optional[str]            # MIME type
    created_at: Optional[datetime]      # File creation timestamp
    modified_at: Optional[datetime]     # File last modification timestamp
    crc32: Optional[str]                # CRC32 checksum
    sha256: Optional[str]               # SHA256 hash for deduplication/integrity
    page_count: Optional[int]           # Number of pages (for documents)
    author: Optional[str]               # Document author (from PDF metadata)
    title: Optional[str]                # Document title (from PDF metadata)
    subject: Optional[str]              # Document subject (from PDF metadata)
    image_width: Optional[int]          # Image width in pixels (for images)
    image_height: Optional[int]         # Image height in pixels (for images)
```

#### 3.2.2 DocumentElement
Represents a structural element extracted from the document (paragraph, table, key-value pair, etc.). Elements are embedded as a list within the Document model.

```
DocumentElement(BaseModel):
    id: str                             # Globally unique element ID (deterministic hash)
    page_id: str                        # Reference to the page containing this element
    page_number: int                    # 1-based page number
    offset: int                         # Character offset in the original content
    short_id: Optional[str]             # Short element reference ID (e.g., "p0", "t1", "kv2")
    type: DocumentElementTypeEnum       # Element type
    element_data: dict                  # Raw element data from the parsing engine
```

**ID Generation**: Element IDs are deterministically generated from `(document_id, page_number, offset)` using MD5 hashing. This ensures idempotent re-parsing.

**Short ID Convention**:
- Paragraphs: `p{index}` (e.g., `p0`, `p1`, `p12`)
- Tables: `t{index}` (e.g., `t0`, `t1`)
- Key-Value Pairs: `kv{index}` (e.g., `kv0`, `kv1`)
- Other: `el{index}`

Where `{index}` is the global element offset-sorted index within the document.

### 3.3 Collection Models

#### 3.3.1 Document (unified File + Document)
Since one file = one document in mydocs2, these are combined into a single model stored in the `documents` collection.

```
Document(MongoBaseModel):
    # --- File-level fields ---
    file_name: str                              # Original filename
    file_type: FileTypeEnum                     # Detected file type
    original_path: str                          # Original file path/URI
    storage_mode: StorageModeEnum               # managed or external
    storage_backend: StorageBackendEnum          # local, azure_blob, s3, etc.
    managed_path: Optional[str]                 # Path in managed storage (if managed)
    file_metadata: Optional[FileMetadata]       # File-level metadata

    # --- Document-level fields ---
    status: DocumentStatusEnum = "new"          # Processing status
    document_type: DocumentTypeEnum = "generic" # Document classification
    locked: bool = False                        # Processing lock flag

    content: Optional[str]                      # Full clean text content (no element refs)
    content_type: Optional[str]                 # MIME type of content field
    parser_engine: Optional[str]                # Which parsing engine was used
    parser_config_hash: Optional[str]           # Hash of the parser config used

    elements: Optional[List[DocumentElement]]   # Extracted structural elements

    tags: List[str] = []                        # User-assignable tags for organization

    created_at: Optional[datetime]
    modified_at: Optional[datetime]

    class Settings:
        name = "documents"
```

**ID Generation**: Document IDs are deterministically generated from the SHA256 hash of the file content (or from `(storage_backend, original_path)` for external files). This enables deduplication.

**Tags**: Documents can be tagged with arbitrary string labels. Tags support:
- Organizing documents by topic, project, or category
- Filtering and searching by tag
- Future: creating "cases" (groupings) from tagged documents

#### 3.3.2 DocumentPage
Represents a single page of a parsed document. Stored in a separate `pages` collection for granular search and retrieval.

```
DocumentPage(MongoBaseModel):
    document_id: str                    # Reference to parent document
    page_number: int                    # 1-based page number

    content: str                        # Clean text content (for full-text search, no element refs)
    content_markdown: str               # Markdown with element references ([short_id] prefix)
    content_html: Optional[str]         # HTML with element references (id attributes)

    height: Optional[float]             # Page height in page units
    width: Optional[float]              # Page width in page units
    unit: Optional[str]                 # Unit of measurement (e.g., "inch", "pixel")

    class Settings:
        name = "pages"
```

**ID Generation**: Page IDs are deterministically generated from `(document_id, page_number)` using MD5 hashing.

**Content Fields**:
- `content`: Plain text from page lines, concatenated with newlines. Used for full-text search. No element references or markup.
- `content_markdown`: Structured markdown with element short_id references as `[short_id]` prefixes. Elements grouped by type (Paragraphs, Tables, Key-Value Pairs) with `###` headers. Used for LLM context.
- `content_html`: Structured HTML with element IDs as `id` attributes on elements. Elements grouped by type with `<h3>` headers. Used for UI rendering with element highlighting.

---

## 4. Element Reference System

The element reference system links extracted text back to visual regions in the original document. This enables:
- Highlighting source regions in the UI when viewing extracted content
- Providing citations with polygon coordinates for LLM-extracted answers

### 4.1 Element References in Markdown
Short IDs appear as bracketed prefixes in markdown content:

```markdown
### Paragraphs

[p0] #### Document Title
[p1] This is the first paragraph of content.
[p2] **[pageFooter]** Page 1 of 10

### Tables

Table [t0]

| Row # | Column A | Column B |
| --- | --- | --- |
| 1 | Value 1 | Value 2 |

### Key-Value Pairs

[kv0] **Policy Number** = ABC-123
[kv1] **Effective Date** = 2024-01-01
```

### 4.2 Element References in HTML
Element IDs appear as `id` attributes on HTML elements:

```html
<h3>Paragraphs</h3>
<h4 id="p0">Document Title</h4>
<p id="p1">This is the first paragraph of content.</p>
<p id="p2" data-role="pageFooter">[pageFooter] Page 1 of 10</p>

<h3>Tables</h3>
<table id="t0">
  <thead>
    <tr><th>Row #</th><th>Column A</th><th>Column B</th></tr>
  </thead>
  <tbody>
    <tr><td>1</td><td>Value 1</td><td>Value 2</td></tr>
  </tbody>
</table>

<h3>Key-Value Pairs</h3>
<div id="kv0" class="kv-pair"><strong class="key">Policy Number</strong> = <span class="value">ABC-123</span></div>
```

### 4.3 Polygon Data
Each `DocumentElement` stores its raw `element_data` from the parsing engine, which includes bounding region information:
- `bounding_regions[].polygon`: List of coordinate points defining the element boundary on the page
- `bounding_regions[].page_number`: Which page the element appears on

The polygon coordinates, combined with `DocumentPage.width`, `DocumentPage.height`, and `DocumentPage.unit`, enable precise visual highlighting in the UI.

---

## 5. Parsing Pipeline

### 5.1 Pipeline Stages

```
[Input]              [File Discovery]     [Ingestion]          [Parsing]           [Embedding]
 file/folder  --->   filter supported  -> store/register  ->  parse with DI  ->  embed pages
 path/URI            formats              in DB                extract elements    & documents
                                                               build pages
```

### 5.2 Detailed Flow

1. **File Discovery**
   - Accept file path, list of paths, or folder path
   - For folders: recursively list all files, filter by supported formats
   - For each file: determine `FileTypeEnum` from extension and/or MIME type

2. **Ingestion** (per file)
   - Compute file metadata (size, timestamps, SHA256 hash, etc.)
   - Check for existing document with same hash (deduplication)
   - **Managed mode**: Copy file to managed storage, record `managed_path`
   - **External mode**: Write sidecar metadata JSON, record `original_path`
   - Create `Document` record in database with status `NEW`

3. **Parsing** (per document)
   - Acquire processing lock on the document (set `locked = True`)
   - Update status to `PARSING`
   - Send file to parsing engine (Azure DI initially)
   - Cache raw parsing results as `<filepath>.di.json` for reprocessing
   - Extract elements (paragraphs, tables, key-value pairs) and assign short IDs
   - Save elements to document
   - Build page content (clean text, markdown with refs, HTML with refs)
   - Save pages to database
   - Update status to `PARSED`
   - Release processing lock

4. **Embedding** (per document, if configured)
   - Generate vector embeddings for document content
   - Generate vector embeddings for each page's content_markdown
   - Store embedding vectors in the document/page records
   - Cache embeddings as JSON files for reprocessing

### 5.3 Error Handling
- If parsing fails, set status to `FAILED` and release the lock
- If a document is already locked, raise `DocumentLockedException` and skip
- Unsupported file formats are recorded with status `NOT_SUPPORTED`
- All errors are logged with document context for debugging

### 5.4 Idempotency
- Document and page IDs are deterministic (hash-based)
- Re-parsing the same file produces the same IDs and overwrites previous data
- Parser config hash is stored to detect when re-parsing with different settings is needed

---

## 6. Parsing Engines

### 6.1 Base Parser Interface

All parsing engines must implement the `DocumentParser` abstract base class:

```
class DocumentParser(ABC):
    """
    Abstract base for document parsing.
    Used as an async context manager to handle document locking.
    """
    def __init__(self, document: Document, parser_config: ParserConfig): ...
    async def __aenter__(self) -> DocumentParser: ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool: ...

    @abstractmethod
    async def parse(self) -> Document:
        """Parse the document and return it with elements and pages populated."""
        ...
```

The context manager pattern handles:
- Creating/loading the document record
- Acquiring and releasing the processing lock
- Error logging and cleanup

### 6.2 Azure Document Intelligence Parser

**Priority**: P0 (initial implementation)

| Setting | Default | Description |
|---------|---------|-------------|
| `azure_di_model` | `prebuilt-layout` | DI model to use |
| `output_content_format` | `markdown` | Output format from DI |
| `features` | `["keyValuePairs"]` | Additional features to enable |
| `api_version` | `2024-11-30` | Azure DI API version |

**Processing steps**:
1. Send file bytes to Azure DI `begin_analyze_document`
2. Poll for result
3. Cache result as `<filepath>.di.json`
4. Extract elements from `paragraphs`, `tables`, `key_value_pairs`
5. Generate deterministic element IDs and short IDs
6. Build page content from `pages[].lines` (clean content) and elements (markdown/HTML)

### 6.3 Future Parsers

| Engine | Priority | Description |
|--------|----------|-------------|
| **GCP Document AI** | P1 | Google Cloud Document AI |
| **AWS Textract** | P2 | Amazon Textract |
| **Open-source (Unstructured.io)** | P2 | Self-hosted alternative |

All future parsers must normalize their output to the same `DocumentElement` structure and produce consistent markdown/HTML with element references.

---

## 7. Search Capabilities

### 7.1 Full-Text Search

MongoDB Atlas full-text search indices on:
- `documents.content` - Search across entire document text
- `pages.content` - Search within individual pages

Full-text search enables:
- Keyword and phrase search across all ingested documents
- Relevance-ranked results
- Filtering by document tags, file type, status, etc.

**Index definitions** (MongoDB Atlas Search):
```json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "content": { "type": "string", "analyzer": "lucene.standard" },
      "tags": { "type": "string", "analyzer": "lucene.keyword" },
      "file_name": { "type": "string", "analyzer": "lucene.standard" },
      "status": { "type": "string", "analyzer": "lucene.keyword" },
      "document_type": { "type": "string", "analyzer": "lucene.keyword" }
    }
  }
}
```

For the `pages` collection:
```json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "content": { "type": "string", "analyzer": "lucene.standard" },
      "document_id": { "type": "string", "analyzer": "lucene.keyword" }
    }
  }
}
```

### 7.2 Vector Search

Vector embeddings are generated for semantic search using configurable embedding models.

#### 7.2.1 Embedding Configuration

```
EmbeddingConfig(BaseModel):
    model: str = "text-embedding-3-large"       # Embedding model name
    field_to_embed: str = "content_markdown"     # Source field for embedding
    target_field: str                            # Field name to store the vector
                                                  # Convention: emb_{field}_{model_slug}
    dimensions: int = 3072                       # Vector dimensions
```

#### 7.2.2 Vector Index Definition

MongoDB Atlas vector search index on the `pages` collection:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "emb_content_markdown_text_embedding_3_large",
      "similarity": "dotProduct",
      "numDimensions": 3072
    },
    { "type": "filter", "path": "document_id" }
  ]
}
```

#### 7.2.3 Retrieval

Two retriever patterns are supported:

1. **Vector Retriever**: Uses MongoDB Atlas Vector Search with pre-filtering by `document_id` to find semantically similar pages.

2. **Pages Retriever**: Directly fetches specific pages by ID (used when page numbers are known, e.g., from split/classify results).

Both return pages with their `content_markdown` (or configurable content field) for use as LLM context.

---

## 8. Configuration System

### 8.1 Parser Configuration

Parser behavior is controlled via a YAML-based configuration system.

```
ParserConfig(BaseConfig):
    config_name: str = "parser"
    azure_di_model: str = "prebuilt-layout"
    azure_di_kwargs: dict = {
        "output_content_format": "markdown",
        "features": ["keyValuePairs"]
    }
    page_embeddings: Optional[List[EmbeddingConfig]]
    document_embeddings: Optional[List[EmbeddingConfig]]
    use_cache: bool = False
```

Configuration is loaded from YAML files with the following precedence:
1. Hardcoded defaults in the `ParserConfig` class
2. Overrides from `<config_root>/parser.yml`

The `BaseConfig` system supports:
- YAML file loading and merging
- Recursive field merging (dicts, lists, nested models)
- Deterministic serialization and hashing for change detection

### 8.2 Configuration File Layout

```
config/
  parser.yml                    # Global parser configuration
```

Example `parser.yml`:
```yaml
azure_di_model: prebuilt-layout
azure_di_kwargs:
  output_content_format: markdown
  features:
    - keyValuePairs
use_cache: true
page_embeddings:
  - model: text-embedding-3-large
    field_to_embed: content_markdown
    target_field: emb_content_markdown_text_embedding_3_large
    dimensions: 3072
document_embeddings:
  - model: text-embedding-3-large
    field_to_embed: content
    target_field: emb_content_text_embedding_3_large
    dimensions: 3072
```

### 8.3 Application Configuration

Environment-variable-based configuration for infrastructure settings:

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGO_URL` | Yes | MongoDB connection URL |
| `MONGO_USER` | Yes | MongoDB username |
| `MONGO_PASSWORD` | Yes | MongoDB password |
| `MONGO_DB_NAME` | Yes | MongoDB database name |
| `AZURE_DI_ENDPOINT` | Yes* | Azure DI endpoint URL |
| `AZURE_DI_API_KEY` | Yes* | Azure DI API key |
| `LLM_API_KEY` | Yes | API key for LLM/embedding service |
| `LLM_API_BASE` | Yes | Base URL for LLM/embedding service |
| `DATA_FOLDER` | No | Root data folder (default: `./data`) |
| `CONFIG_ROOT` | No | Root config folder (default: `./config`) |
| `SERVICE_NAME` | No | Service identifier (default: `mydocs2`) |

*Required when Azure DI parser is used.

---

## 9. Database Architecture

### 9.1 ODM Layer

The application uses a custom Pydantic-based ODM (`MongoBaseModel`) providing:
- Pydantic model validation and serialization
- `id` field mapped to MongoDB `_id`
- Deterministic ID generation via MD5 hashing of composite keys
- Both synchronous (`save`, `find`, `get`) and asynchronous (`asave`, `afind`, `aget`) CRUD operations
- Upsert semantics on save (replace_one with upsert=True)
- Aggregation pipeline support
- Bulk insert operations

### 9.2 Collections

| Collection | Model | Description |
|------------|-------|-------------|
| `documents` | `Document` | Unified file + document records |
| `pages` | `DocumentPage` | Individual page content and embeddings |

### 9.3 Indexes

#### Standard Indexes
```
documents:
  - { status: 1 }
  - { tags: 1 }
  - { file_type: 1 }
  - { created_at: -1 }
  - { "file_metadata.sha256": 1 }         # For deduplication

pages:
  - { document_id: 1, page_number: 1 }    # Compound for page lookup
  - { document_id: 1 }                     # For all pages of a document
```

#### Atlas Search Indexes
- `ft_documents` - Full-text search on `documents.content`
- `ft_pages` - Full-text search on `pages.content`

#### Atlas Vector Search Indexes
- `vec_pages_large_dot` - Vector search on page embeddings

### 9.4 Future Database Backends

| Backend | Priority | Notes |
|---------|----------|-------|
| **MongoDB** | P0 (initial) | Primary backend with Atlas Search and Vector Search |
| **PostgreSQL** | P2 (future) | With pgvector extension for vector search |
| **SQLite** | P3 (future) | For local/embedded deployments |

A database abstraction layer should be designed to allow swapping backends. The initial implementation targets MongoDB only, but the ODM interface should be generic enough to support future backends.

---

## 10. Migration System

### 10.1 Index Migrations

Database index migrations are implemented as standalone Python scripts in a `migrations/` directory:

```
migrations/
  001_fulltext_documents.py
  002_fulltext_pages.py
  003_vector_pages_large_dot.py
```

Each migration script uses utility functions:
- `create_or_replace_index(collection_name, index_name, definition, type, skip_if_exists)`
- `create_simple_index(collection, definition)`

Vector search index creation example:
```python
definition = {
    "fields": [
        {
            "type": "vector",
            "path": "emb_content_markdown_text_embedding_3_large",
            "similarity": "dotProduct",
            "numDimensions": 3072
        },
        {"type": "filter", "path": "document_id"}
    ]
}
create_or_replace_index("pages", "vec_pages_large_dot", definition, skip_if_exists=True)
```

---

## 11. Caching Strategy

The parsing engine supports caching at multiple levels to avoid redundant processing:

| Cache | Location | Description |
|-------|----------|-------------|
| **DI Results** | `<filepath>.di.json` | Raw Azure DI response, avoids re-calling the API |
| **Document Embeddings** | `<filepath>.doc.<field>.json` | Cached embedding vectors for document |
| **Page Embeddings** | `<filepath>.pages.<field>.json` | Cached embedding vectors for pages |

Caching is controlled by the `use_cache` flag in `ParserConfig`. When enabled:
- Before calling Azure DI, check for cached `.di.json` file
- Before computing embeddings, check for cached embedding JSON files
- Cached data is loaded directly, skipping the API call

---

## 12. API Contracts (for FastAPI Backend)

The parsing engine exposes the following operations to be wrapped by FastAPI endpoints:

### 12.1 Ingest Files
```
POST /api/v1/documents/ingest
Body: {
    "source": "path/to/file/or/folder",
    "storage_mode": "managed" | "external",
    "tags": ["optional", "tags"],
    "recursive": true
}
Response: {
    "documents": [{ "id": "...", "file_name": "...", "status": "new" }],
    "skipped": [{ "path": "...", "reason": "unsupported_format" }]
}
```

### 12.2 Parse Documents
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

### 12.3 Batch Parse
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

### 12.4 Search Documents
```
POST /api/v1/documents/search
Body: {
    "query": "search terms",
    "search_type": "fulltext" | "vector" | "hybrid",
    "filters": {
        "tags": ["tag1"],
        "file_type": "pdf",
        "document_ids": ["id1", "id2"]
    },
    "top_k": 10,
    "include_pages": true
}
```

### 12.5 Get Document
```
GET /api/v1/documents/{document_id}
Response: { ... full document model ... }
```

### 12.6 Get Pages
```
GET /api/v1/documents/{document_id}/pages
GET /api/v1/documents/{document_id}/pages/{page_number}
```

### 12.7 Manage Tags
```
POST /api/v1/documents/{document_id}/tags
Body: { "tags": ["new_tag"] }

DELETE /api/v1/documents/{document_id}/tags/{tag}
```

---

## 13. Module Structure

```
mydocs2/
  parsing/
    __init__.py
    models.py                   # Document, DocumentPage, DocumentElement, enums
    config.py                   # ParserConfig, EmbeddingConfig
    base_parser.py              # DocumentParser ABC
    pipeline.py                 # Ingestion and parsing orchestration
    azure_di/
      __init__.py
      parser.py                 # AzureDIDocumentParser implementation
      html.py                   # Element -> HTML conversion
      markdown.py               # Element -> Markdown conversion
    storage/
      __init__.py
      base.py                   # FileStorage ABC
      local.py                  # LocalFileStorage implementation
  common/
    __init__.py
    config.py                   # Application config (env vars)
    base_config.py              # BaseConfig with YAML loading
    mongo/
      __init__.py
      base_model.py             # MongoBaseModel ODM
      utils.py                  # Connection management, ID generation
      operations.py             # Index management utilities
  migrations/
    001_fulltext_documents.py
    002_fulltext_pages.py
    003_vector_pages_large_dot.py
```

---

## 14. Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic` | Data models and validation |
| `pymongo` | Synchronous MongoDB driver |
| `motor` | Asynchronous MongoDB driver |
| `azure-ai-documentintelligence` | Azure DI client |
| `langchain-openai` | OpenAI embeddings |
| `langchain-mongodb` | MongoDB Atlas Vector Search integration |
| `python-dotenv` | Environment variable loading |
| `pyyaml` | YAML configuration loading |

---

## 15. Non-Functional Requirements

### 15.1 Performance
- File ingestion should support batch processing of folders with hundreds of files
- Parsing should be parallelizable (multiple documents can be parsed concurrently via locking)
- Embedding generation should support caching to avoid redundant API calls

### 15.2 Reliability
- Document locking prevents concurrent parsing of the same document
- Idempotent parsing: re-running on the same file produces the same result
- Parser config hashing detects when re-parsing is needed due to config changes
- Failed parsing is recorded with status for retry

### 15.3 Extensibility
- New parsing engines can be added by implementing `DocumentParser`
- New storage backends can be added by implementing `FileStorage`
- New file formats can be added by extending `FileTypeEnum` and format detection
- New element types can be added by extending `DocumentElementTypeEnum` and HTML/Markdown converters
- The database layer is designed to be backend-agnostic through the ODM pattern

### 15.4 Observability
- Structured logging throughout the pipeline
- Document status tracking for monitoring pipeline health
- Parser config hash for audit trail of processing parameters
