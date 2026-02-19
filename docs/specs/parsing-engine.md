# Parsing Engine Specification

**Package**: `mydocs.parsing`
**Version**: 1.2
**Status**: Draft

**Related Specs**: [retrieval-engine.md](retrieval-engine.md) (search & embeddings), [backend.md](backend.md) (HTTP API & app config), [migrations.md](migrations.md) (index migrations), [cli.md](cli.md) (CLI interface), [sync.md](sync.md) (storage-to-DB sync)

---

## 1. Overview

The parsing engine is responsible for ingesting files (initially PDFs), extracting structured content using document intelligence services (initially Azure Document Intelligence), and storing the results as queryable documents.

The engine transforms raw files into a three-level hierarchy:

```
File -> Document -> DocumentPage
                 -> DocumentElement (embedded in Document)
```

Since in mydocs one file always corresponds to one document, the `File` and `Document` are stored in the same MongoDB collection (`documents`) as a unified model. Pages are stored separately in a `pages` collection for granular retrieval.

Search and retrieval capabilities are specified in [retrieval-engine.md](retrieval-engine.md). HTTP API contracts are specified in [backend.md](backend.md).

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
- A **metadata sidecar** (`<doc_id>.metadata.json`) is written alongside the managed file for DB recovery (see [sync.md](sync.md) for `MetadataSidecar` schema)
- Initial backend: local filesystem mapped to `./data/managed/`
- Future backends: Azure Blob Storage, S3, GCP Cloud Storage

#### 2.3.2 External Mode
- The file **remains at its original location**
- A **metadata sidecar** (`<doc_id>.metadata.json`) is written alongside the original file (same directory) for DB recovery
- The original path/URI is recorded for access
- Useful for large file repositories where copying is impractical

#### 2.3.3 Metadata Sidecar

Both storage modes write a `MetadataSidecar` JSON file during ingestion. The sidecar contains all fields needed to reconstruct a `Document` record from disk, enabling database recovery via the sync module. The `MetadataSidecar` model is defined in `mydocs/models.py`; see [sync.md](sync.md) for the full schema and sync algorithm.

### 2.4 Managed File Store Backends

| Backend | Priority | Description |
|---------|----------|-------------|
| **Local Filesystem** | P0 (initial) | Files stored under `./data/managed/` |
| **Azure Blob Storage** | P1 (future) | Azure Blob container |
| **AWS S3** | P2 (future) | S3 bucket |
| **GCP Cloud Storage** | P2 (future) | GCS bucket |

---

## 3. Data Models

> **Note**: Document and page models (`Document`, `DocumentPage`, enums, embedded models) have moved to `mydocs/models.py`. The file `mydocs/parsing/models.py` is a re-export stub that imports everything from `mydocs.models` for backward compatibility.

All collection models extend `MongoBaseModel` from the `lightodm` library. Lightodm provides:
- Pydantic v2 model validation and serialization
- `id` field mapped to MongoDB `_id`
- **Composite key** support: when `Settings.composite_key` is defined as a list of field names, the `id` is automatically computed as an MD5 hash of those field values on model instantiation. This ensures deterministic, idempotent IDs.
- Both synchronous (`save`, `find`, `get`, `find_one`, `count`, `update_one`, `delete`) and asynchronous (`asave`, `afind`, `aget`, `afind_one`, `acount`, `aupdate_one`, `adelete`) CRUD operations
- Upsert semantics on save (`replace_one` with `upsert=True`)
- Aggregation pipeline support (`aggregate`, `aaggregate`)
- Bulk insert operations (`insert_many`, `ainsert_many`)

### 3.1 Enumerations

#### 3.1.1 FileTypeEnum
Identifies the file format.

```python
class FileTypeEnum(StrEnum):
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

```python
class StorageModeEnum(StrEnum):
    MANAGED = "managed"
    EXTERNAL = "external"
```

#### 3.1.3 StorageBackendEnum
Identifies the storage backend for managed files and file sources.

```python
class StorageBackendEnum(StrEnum):
    LOCAL = "local"
    AZURE_BLOB = "azure_blob"
    S3 = "s3"
    GCS = "gcs"
    ONEDRIVE = "onedrive"
```

#### 3.1.4 DocumentStatusEnum
Tracks the processing status of a document.

```python
class DocumentStatusEnum(StrEnum):
    NEW = "new"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_SUPPORTED = "not_supported"
```

#### 3.1.5 DocumentElementTypeEnum
Types of structural elements extracted from documents.

```python
class DocumentElementTypeEnum(StrEnum):
    PARAGRAPH = "paragraph"
    TABLE = "table"
    KEY_VALUE_PAIR = "key_value_pair"
    IMAGE = "image"
    BARCODE = "barcode"
```

#### 3.1.6 DocumentTypeEnum
Classification of the document (initially only GENERIC).

```python
class DocumentTypeEnum(StrEnum):
    GENERIC = "generic"
```

### 3.2 Embedded Models (not stored as separate collections)

#### 3.2.1 FileMetadata
Stores filesystem and format-specific metadata about the original file.

```python
class FileMetadata(BaseModel):
    size_bytes: Optional[int] = None        # File size in bytes
    mime_type: Optional[str] = None         # MIME type
    created_at: Optional[datetime] = None   # File creation timestamp
    modified_at: Optional[datetime] = None  # File last modification timestamp
    crc32: Optional[str] = None             # CRC32 checksum
    sha256: Optional[str] = None            # SHA256 hash for deduplication/integrity
    page_count: Optional[int] = None        # Number of pages (for documents)
    author: Optional[str] = None            # Document author (from PDF metadata)
    title: Optional[str] = None             # Document title (from PDF metadata)
    subject: Optional[str] = None           # Document subject (from PDF metadata)
    image_width: Optional[int] = None       # Image width in pixels (for images)
    image_height: Optional[int] = None      # Image height in pixels (for images)
```

#### 3.2.2 DocumentElement
Represents a structural element extracted from the document (paragraph, table, key-value pair, etc.). Elements are embedded as a list within the Document model.

```python
class DocumentElement(BaseModel):
    id: str                                 # Globally unique element ID (deterministic hash)
    page_id: str                            # Reference to the page containing this element
    page_number: int                        # 1-based page number
    offset: int                             # Character offset in the original content
    short_id: Optional[str] = None          # Short element reference ID (e.g., "p0", "t1", "kv2")
    type: DocumentElementTypeEnum           # Element type
    element_data: dict                      # Raw element data from the parsing engine
```

**ID Generation**: Element IDs are generated using `lightodm.generate_composite_id([document_id, page_number, offset])`. This ensures idempotent re-parsing produces identical element IDs.

**Short ID Convention**:
- Paragraphs: `p{index}` (e.g., `p0`, `p1`, `p12`)
- Tables: `t{index}` (e.g., `t0`, `t1`)
- Key-Value Pairs: `kv{index}` (e.g., `kv0`, `kv1`)
- Other: `el{index}`

Where `{index}` is the global element offset-sorted index within the document.

### 3.3 Collection Models

#### 3.3.1 Document (unified File + Document)
Since one file = one document in mydocs, these are combined into a single model stored in the `documents` collection.

```python
class Document(MongoBaseModel):
    # --- File-level fields ---
    content_hash: str                                   # Mirrors file_metadata.sha256
    file_name: str                                      # Stem of the filename (no extension)
    original_file_name: str                             # Original filename with extension
    file_type: FileTypeEnum                             # Detected file type
    original_path: str                                  # Original file path/URI
    storage_mode: StorageModeEnum                       # managed or external
    storage_backend: StorageBackendEnum                 # local, azure_blob, s3, etc.
    managed_path: Optional[str] = None                  # Path in managed storage (if managed)
    file_metadata: Optional[FileMetadata] = None        # File-level metadata

    # --- Document-level fields ---
    status: DocumentStatusEnum = DocumentStatusEnum.NEW # Processing status
    document_type: DocumentTypeEnum = DocumentTypeEnum.GENERIC  # Classification
    locked: bool = False                                # Processing lock flag

    content: Optional[str] = None                       # Full clean text (no element refs)
    content_type: Optional[str] = None                  # MIME type of content field
    parser_engine: Optional[str] = None                 # Which parsing engine was used
    parser_config_hash: Optional[str] = None            # Hash of the parser config used

    elements: Optional[List[DocumentElement]] = None    # Extracted structural elements

    tags: List[str] = Field(default_factory=list)       # User-assignable tags

    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None

    class Settings:
        name = "documents"
        composite_key = ["original_path", "content_hash"]
```

**ID Generation via composite key**: The `Settings.composite_key = ["original_path", "content_hash"]` declaration causes `lightodm` to automatically compute the document `id` as `MD5(original_path + content_hash)` on model instantiation. The `content_hash` field mirrors `file_metadata.sha256` and decouples document identity from the storage backend, making cross-backend migration natural — the same document gets the same ID regardless of where it's stored. This means:
- The same file imported twice produces the same document ID (upsert/dedup)
- Re-ingestion of the same path is idempotent
- Migration between storage backends preserves document IDs
- No manual ID management is needed

**Tags**: Documents can be tagged with arbitrary string labels. Tags support:
- Organizing documents by topic, project, or category
- Filtering and searching by tag
- Future: creating "cases" (groupings) from tagged documents

#### 3.3.2 DocumentPage
Represents a single page of a parsed document. Stored in a separate `pages` collection for granular search and retrieval.

```python
class DocumentPage(MongoBaseModel):
    document_id: str                        # Reference to parent document
    page_number: int                        # 1-based page number

    content: Optional[str] = None           # Clean text (for full-text search, no element refs)
    content_markdown: Optional[str] = None  # Markdown with element references ([short_id] prefix)
    content_html: Optional[str] = None      # HTML with element references (id attributes)

    height: Optional[float] = None          # Page height in page units
    width: Optional[float] = None           # Page width in page units
    unit: Optional[str] = None              # Unit of measurement (e.g., "inch", "pixel")

    class Settings:
        name = "pages"
        composite_key = ["document_id", "page_number"]
```

**ID Generation via composite key**: `Settings.composite_key = ["document_id", "page_number"]` causes the page `id` to be automatically computed as `MD5(document_id + page_number)`. Re-parsing the same document produces the same page IDs, enabling clean upserts.

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
   - Create `Document` instance -- the composite key auto-generates the ID from `(original_path, content_hash)`, so duplicate imports are automatically handled via upsert
   - **Managed mode**: Copy file to managed storage, record `managed_path`
   - **External mode**: Write sidecar metadata JSON, record `original_path`
   - Save document to database (upsert via `asave()`) with status `NEW`

3. **Parsing** (per document)
   - Acquire processing lock on the document (set `locked = True`)
   - Update status to `PARSING`
   - Send file to parsing engine (Azure DI initially)
   - Cache raw parsing results as `<filepath>.di.json` for reprocessing
   - Extract elements (paragraphs, tables, key-value pairs) and assign short IDs
   - Save elements to document
   - Build page content (clean text, markdown with refs, HTML with refs)
   - Save pages to database (each page's composite key `[document_id, page_number]` ensures idempotent upserts)
   - Update status to `PARSED`
   - Release processing lock

4. **Embedding** (per document, if configured)
   - Generate vector embeddings for document content using `litellm.aembedding()`
   - Generate vector embeddings for each page's content_markdown
   - Store embedding vectors in the document/page records via `aupdate_one()`
   - Cache embeddings as JSON files for reprocessing

### 5.3 Error Handling
- If parsing fails, set status to `FAILED` and release the lock
- If a document is already locked, raise `DocumentLockedException` and skip
- Unsupported file formats are recorded with status `NOT_SUPPORTED`
- All errors are logged with document context using `tinystructlog` structured logging

### 5.4 Idempotency
- Document and page IDs are deterministic via lightodm composite keys
- Re-parsing the same file produces the same IDs and overwrites previous data via upsert
- Parser config hash is stored to detect when re-parsing with different settings is needed

---

## 6. Parsing Engines

### 6.1 Base Parser Interface

All parsing engines must implement the `DocumentParser` abstract base class:

```python
class DocumentParser(ABC):
    """
    Abstract base for document parsing.
    Used as an async context manager to handle document locking.
    """
    def __init__(self, document: Document, parser_config: ParserConfig):
        self.document = document
        self.parser_config = parser_config
        self.pages: List[DocumentPage] = []

    async def __aenter__(self) -> "DocumentParser":
        """Load existing document state and acquire processing lock."""
        ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Release processing lock and handle errors."""
        ...

    @abstractmethod
    async def parse(self) -> Document:
        """Parse the document and return it with elements and pages populated."""
        ...
```

The context manager pattern handles:
- Loading existing document state from the database
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
5. Generate deterministic element IDs using `generate_composite_id()` and assign short IDs
6. Build page content from `pages[].lines` (clean content) and elements (markdown/HTML)

### 6.3 Future Parsers

| Engine | Priority | Description |
|--------|----------|-------------|
| **GCP Document AI** | P1 | Google Cloud Document AI |
| **AWS Textract** | P2 | Amazon Textract |
| **Open-source (Unstructured.io)** | P2 | Self-hosted alternative |

All future parsers must normalize their output to the same `DocumentElement` structure and produce consistent markdown/HTML with element references.

---

## 7. Configuration System

### 7.1 Parser Configuration

Parser behavior is controlled via a YAML-based configuration system.

```python
class ParserConfig(BaseConfig):
    config_name: str = "parser"
    azure_di_model: str = "prebuilt-layout"
    azure_di_kwargs: dict = {
        "output_content_format": "markdown",
        "features": ["keyValuePairs"]
    }
    page_embeddings: Optional[List[EmbeddingConfig]] = None
    document_embeddings: Optional[List[EmbeddingConfig]] = None
    use_cache: bool = False
```

Configuration is loaded from YAML files with the following precedence:
1. Hardcoded defaults in the `ParserConfig` class
2. Overrides from `<config_root>/parser.yml`

The `BaseConfig` system supports:
- YAML file loading and merging
- Recursive field merging (dicts, lists, nested models)
- Deterministic serialization and hashing for change detection

### 7.2 Configuration File Layout

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

Application-level configuration (environment variables) is documented in [backend.md](backend.md) Section 2.

---

## 8. Database Architecture

### 8.1 ODM Layer

The application uses `lightodm` (Lightweight MongoDB ODM) as its database abstraction layer. Lightodm is installed as a pip dependency and provides:
- `MongoBaseModel` base class extending Pydantic `BaseModel`
- `id` field automatically mapped to MongoDB `_id`
- `Settings.composite_key` for declarative deterministic ID generation
- `generate_composite_id(values)` utility for manual composite ID generation (used for embedded models like `DocumentElement`)
- Both synchronous and asynchronous CRUD operations
- Singleton `MongoConnection` manager with thread-safe sync (pymongo) and async (motor) clients
- Connection configured via environment variables (`MONGO_URL`, `MONGO_USER`, `MONGO_PASSWORD`, `MONGO_DB_NAME`)

No separate `pymongo` or `motor` dependencies are needed in the application -- they are transitive dependencies of `lightodm`.

### 8.2 Collections

| Collection | Model | Composite Key | Description |
|------------|-------|---------------|-------------|
| `documents` | `Document` | `[original_path, content_hash]` | Unified file + document records |
| `pages` | `DocumentPage` | `[document_id, page_number]` | Individual page content and embeddings |

### 8.3 Standard Indexes

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

Atlas Search and Vector Search indexes are defined in [retrieval-engine.md](retrieval-engine.md). Index migration scripts are documented in [migrations.md](migrations.md).

### 8.4 Future Database Backends

| Backend | Priority | Notes |
|---------|----------|-------|
| **MongoDB** | P0 (initial) | Primary backend with Atlas Search and Vector Search |
| **PostgreSQL** | P2 (future) | With pgvector extension for vector search |
| **SQLite** | P3 (future) | For local/embedded deployments |

A database abstraction layer should be designed to allow swapping backends. The initial implementation targets MongoDB only via lightodm.

---

## 9. Caching Strategy

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

## 10. Logging

The application uses `tinystructlog` for structured, context-aware logging throughout the parsing pipeline.

### 10.1 Logger Usage

```python
from tinystructlog import get_logger

log = get_logger(__name__)

log.info("Processing document")
log.error("Parsing failed", exc_info=True)
```

### 10.2 Context-Aware Logging

Use `set_log_context()` and `log_context()` to attach contextual information (document ID, file name, etc.) to all log messages within a scope:

```python
from tinystructlog import set_log_context, log_context

# Set context for the duration of parsing
set_log_context(document_id=doc.id, file_name=doc.file_name)
log.info("Starting parse")  # Includes document_id and file_name in output

# Or use context manager for temporary context
with log_context(parser="azure_di"):
    log.info("Calling Azure DI")  # Includes parser=azure_di
```

### 10.3 Log Output Format

Default format: `[timestamp] [LEVEL] [module.function:line] [context_key=value ...] message`

Example:
```
[2025-02-10 14:30:45] [INFO] [parser.parse:52] [document_id=abc123 file_name=report.pdf] Starting parse
```

Log level is controlled via `LOG_LEVEL` environment variable (default: `INFO`).

---

## 11. Package Structure

The package is named `mydocs` and managed with `uv`. The parsing engine is a subpackage.

```
mydocs2/                            # Project root
  pyproject.toml                    # uv project configuration
  mydocs/                           # Main package
    __init__.py
    config.py                       # Application config (env vars)
    models.py                       # Canonical document/page/case models, enums
    common/
      __init__.py
      base_config.py                # BaseConfig with YAML loading
    parsing/                        # Parsing subpackage
      __init__.py
      models.py                     # Re-export stub (imports from mydocs.models)
      config.py                     # ParserConfig, EmbeddingConfig
      base_parser.py                # DocumentParser ABC
      pipeline.py                   # Ingestion and parsing orchestration
      azure_di/
        __init__.py
        parser.py                   # AzureDIDocumentParser implementation
        html.py                     # Element -> HTML conversion
        markdown.py                 # Element -> Markdown conversion
      storage/
        __init__.py
        base.py                     # FileStorage ABC
        local.py                    # LocalFileStorage implementation
    retrieval/                      # Retrieval subpackage (see retrieval-engine.md)
      __init__.py
      search.py
      models.py
      embeddings.py
      vector_retriever.py
      fulltext_retriever.py
      hybrid.py
    backend/                        # FastAPI backend (see backend.md)
      __init__.py
      app.py
      routes/
        __init__.py
        documents.py
        search.py
      dependencies.py
    cli/                            # CLI (see cli.md)
      __init__.py
      main.py
      commands/
        __init__.py
        ingest.py
        parse.py
        search.py
        docs.py
        config.py
        migrate.py
      formatters.py
  migrations/                       # Database migrations (see migrations.md)
    001_fulltext_documents.py
    002_fulltext_pages.py
    003_vector_pages_large_dot.py
  config/
    parser.yml
  data/
    managed/                        # Default managed file storage
  docs/
    specs/
      parsing-engine.md             # This file
      retrieval-engine.md           # Search & retrieval spec
      backend.md                    # HTTP API & app config spec
      migrations.md                 # Database migration spec
      cli.md                        # CLI spec
```

---

## 12. Dependencies

Parsing engine dependencies:

| Package | Purpose |
|---------|---------|
| `lightodm` | MongoDB ODM (bundles pymongo + motor) |
| `pydantic` | Data models and validation (transitive via lightodm) |
| `azure-ai-documentintelligence` | Azure Document Intelligence client |
| `litellm` | Unified embedding API for vector generation |
| `pyyaml` | YAML configuration loading |
| `tinystructlog` | Structured context-aware logging |

**Explicitly NOT included** (compared to source projects):
- `pymongo` / `motor` -- transitive dependencies of `lightodm`, not listed directly
- `langchain-openai` / `langchain-mongodb` -- replaced by `litellm` for embeddings; vector search uses raw MongoDB aggregation pipelines

Dependencies for other components are listed in their respective specs: [backend.md](backend.md), [retrieval-engine.md](retrieval-engine.md), [cli.md](cli.md).

---

## 13. Non-Functional Requirements

### 13.1 Performance
- File ingestion should support batch processing of folders with hundreds of files
- Parsing should be parallelizable (multiple documents can be parsed concurrently via locking)
- Embedding generation should support caching to avoid redundant API calls

### 13.2 Reliability
- Document locking prevents concurrent parsing of the same document
- Idempotent parsing via lightodm composite keys: re-running on the same file produces the same IDs
- Parser config hashing detects when re-parsing is needed due to config changes
- Failed parsing is recorded with status for retry

### 13.3 Extensibility
- New parsing engines can be added by implementing `DocumentParser`
- New storage backends can be added by implementing `FileStorage`
- New file formats can be added by extending `FileTypeEnum` and format detection
- New element types can be added by extending `DocumentElementTypeEnum` and HTML/Markdown converters
- The database layer is abstracted through lightodm; future backends (PostgreSQL, SQLite) would require an equivalent ODM adapter

### 13.4 Observability
- Structured context-aware logging via `tinystructlog` throughout the pipeline
- Context variables (document_id, file_name, parser engine) attached to log messages
- Document status tracking for monitoring pipeline health
- Parser config hash for audit trail of processing parameters
