# Extracting Engine Specification

**Package**: `mydocs.extracting`
**Version**: 1.0
**Status**: Draft

**Related Specs**: [parsing-engine.md](parsing-engine.md) (data models, element references), [retrieval-engine.md](retrieval-engine.md) (search & embeddings), [backend.md](backend.md) (HTTP API), [cli.md](cli.md) (CLI interface)

---

## 1. Overview

The extracting engine is responsible for LLM-based information extraction from parsed documents. It supports:

- **Field extraction**: Extracting structured data (dates, names, amounts, classifications) from document content using LLM prompts
- **Document classification & splitting**: Identifying document boundaries and types within multi-document files
- **Custom structure extraction**: Extracting data into arbitrary Pydantic models (line items, instalments, nested objects)

The engine operates on `Document` and `DocumentPage` models from [parsing-engine.md](parsing-engine.md) and uses the retrieval engine from [retrieval-engine.md](retrieval-engine.md) for context selection.

### 1.1 Key Concepts

| Concept | Description |
|---------|-------------|
| **Case** | A container that groups related documents for processing. Has a `type` field (e.g., `"generic"`, `"insurance_claim"`). Stored in the `cases` MongoDB collection. |
| **Case Type** | The `Case.type` value that determines which config directory tree is used. Default: `"generic"`. Maps to `{case.type.lower()}/` in the config hierarchy. |
| **Field** | A named piece of information to extract (e.g., "DateOfLoss", "PolicyNumber"). Replaces "attribute" from prior systems. |
| **Document Type** | A classification that determines which fields and prompts apply (e.g., `claim`, `policy`, `invoice`). Extends `DocumentTypeEnum`. Replaces "attribute_type" from prior systems. |
| **Field Definition** | Configuration for a field: name, description, extraction prompt, data type, allowed values. |
| **Prompt Config** | LLM prompt template and retrieval settings for a group of fields. |
| **Field Result** | The extraction output: value, citation, justification, and optionally polygon references. |
| **Extraction Mode** | Controls output structure: `referenced` (FieldResult with citations/references) or `direct` (raw Pydantic structured output, optionally followed by a reference-inference pass). |
| **Reference Granularity** | Controls how much source-location detail is returned: `full`, `page`, or `none`. |

> **Note — Case model change**: The `Case` model (from `mydocs/models.py`) requires a new `type` field:
>
> ```python
> class Case(MongoBaseModel):
>     name: str
>     type: str = "generic"                        # Case type — determines config directory
>     description: Optional[str] = None
>     document_ids: list[str] = Field(default_factory=list)
>     ...
> ```

---

## 2. Data Models

### 2.1 Enumerations

#### 2.1.1 DocumentTypeEnum (extended)

The extracting engine extends `DocumentTypeEnum` from [parsing-engine.md](parsing-engine.md) with domain-specific types. New document types are registered by adding values to the enum.

```python
class DocumentTypeEnum(StrEnum):
    GENERIC = "generic"          # Default (from parsing engine)
    # Domain-specific types added per deployment:
    # CLAIM = "claim"
    # POLICY = "policy"
    # INVOICE = "invoice"
    # COVERAGE = "coverage"
```

#### 2.1.2 ReferenceGranularity

Controls how much source-location detail is captured during extraction.

```python
class ReferenceGranularity(StrEnum):
    FULL = "full"    # Polygon coordinates, citation, justification, element references
    PAGE = "page"    # Page ID and citation text only
    NONE = "none"    # Value only, no source tracking
```

#### 2.1.3 ContentMode

Controls which content representation is used for element identification in LLM context.

```python
class ContentMode(StrEnum):
    MARKDOWN = "markdown"    # content_markdown with [short_id] references
    HTML = "html"            # content_html with id attributes
```

#### 2.1.4 ExtractionMode

Controls the output structure of extraction results.

```python
class ExtractionMode(StrEnum):
    REFERENCED = "referenced"  # Fields wrapped in FieldResult (citations, references)
    DIRECT = "direct"          # Raw Pydantic model via LLM structured output
```

#### 2.1.5 FieldDataType

Semantic data type hint for extracted field values.

```python
class FieldDataType(StrEnum):
    STRING = "string"
    DATE = "date"
    NUMBER = "number"
    CURRENCY = "currency"
    BOOLEAN = "boolean"
    ENUM = "enum"          # Value must be from value_list
    TEXT = "text"          # Long-form text
```

### 2.2 Field Definition

Defines a single field to extract. Managed in YAML config files and optionally stored in MongoDB for versioning.

```python
class FieldValueOption(BaseModel):
    name: str                                    # Option display name
    prompt: Optional[str] = None                 # Guidance for when to select this option

class FieldRequirement(BaseModel):
    field_name: str                              # Name of required field
    document_type: Optional[str] = None          # From which document_type (if cross-type)

class FieldDefinition(BaseModel):
    name: str                                    # Unique field name (within document_type)
    description: str                             # Business description
    data_type: FieldDataType = FieldDataType.STRING
    prompt: Optional[str] = None                 # Extraction instructions for the LLM
    value_list: Optional[list[FieldValueOption]] = None  # Allowed values (for enum type)
    group: int = 0                               # Extraction group (fields in same group
                                                 # are extracted together in one LLM call)
    inputs: Optional[list[FieldRequirement]] = None  # Dependencies on other fields
```

**Groups**: Fields are organized into groups. All fields in the same group are sent to the LLM in a single call with a shared prompt and retrieval context. Group 0 is the default. Groups execute in parallel.

### 2.3 Field Result

The extraction engine supports two output modes:

**Referenced mode** (`extraction_mode = "referenced"`): The LLM returns `LLMFieldItem` objects containing value, justification, citation, and element references. These are enriched into `FieldResult` objects with polygon data. This is the default.

**Direct mode** (`extraction_mode = "direct"`): A user-supplied Pydantic model is passed directly to the LLM's structured output. The result contains native Python types (str, float, etc.) with no references. Optionally, a second pass can infer references (see Section 4.2, Step 4).

The level of detail in referenced mode depends on `ReferenceGranularity`.

```python
class Reference(BaseModel):
    """Source location in the original document (full granularity only)."""
    document_id: str
    page_id: str
    page_number: int
    page_width: float
    page_height: float
    page_unit: str
    element_type: str                            # "paragraph", "table", "key_value_pair"
    element_short_id: str                        # "p0", "t1", "kv2"
    polygon: list[float]                         # Bounding box [x1, y1, x2, y2, ...]
    llm_reference: Optional[str] = None          # Raw LLM reference string

class PageReference(BaseModel):
    """Lightweight page-level reference (page granularity)."""
    document_id: str
    page_id: str
    page_number: int

class FieldResult(BaseModel):
    """Result of extracting a single field."""
    content: Optional[str] = None                # Extracted value
    justification: Optional[str] = None          # Why this value (full/page granularity)
    citation: Optional[str] = None               # Exact text from document (full/page)
    references: Optional[list[Reference]] = None         # Full granularity only
    page_references: Optional[list[PageReference]] = None  # Page granularity only
    created_by: Optional[str] = None             # Service/model that produced this
    created_at: Optional[datetime] = None
```

When `reference_granularity = "none"`, only `content` is populated. When `"page"`, `content`, `justification`, `citation`, and `page_references` are populated. When `"full"`, all fields including `references` with polygon data.

#### 2.3.1 Reference Inference Models (Direct Mode)

When using direct mode with `infer_references = True`, the reference-inference pass produces the following models:

```python
class FieldReference(BaseModel):
    """Reference annotation for a single leaf field in direct mode."""
    field_path: str                              # JSONPath-like: "line_items[0].amount"
    citation: Optional[str] = None
    justification: Optional[str] = None
    references: Optional[list[Reference]] = None
    page_references: Optional[list[PageReference]] = None

class ReferenceInferenceResult(BaseModel):
    """Output of the reference-inference pass."""
    field_references: list[FieldReference]
```

### 2.4 LLM Input/Output Models

These models define the structured output schema that the LLM must produce.

#### 2.4.1 Default Schema (field extraction)

```python
class LLMFieldItem(BaseModel):
    """Single extracted field from the LLM."""
    name: str                                    # Field name
    content: str                                 # Extracted value (empty if not found)
    justification: str                           # Business-language explanation
    citation: str                                # Exact string from document
    references: list[str]                        # Element references: "d1:1:p2", "d1:3:t5:2"

class LLMFieldsResult(BaseModel):
    """Container for LLM field extraction output."""
    result: list[LLMFieldItem]
```

#### 2.4.2 Custom Schema (structured extraction)

Custom output schemas can be registered for extracting structured data (e.g., line items, nested objects). Each schema is a Pydantic model whose fields are `LLMFieldItem` instances:

```python
# Example: extracting invoice line items
class LLMLineItem(BaseModel):
    description: LLMFieldItem
    quantity: LLMFieldItem
    unit_price: LLMFieldItem
    amount: LLMFieldItem

class LLMLineItemsResult(BaseModel):
    result: list[LLMLineItem]
```

Custom schemas are registered in the schema registry (Section 8.2) and referenced by name in prompt configs.

### 2.5 Extraction Request

```python
class ExtractionRequest(BaseModel):
    """Request to extract fields from documents."""
    case_id: Optional[str] = None                # Case to extract from (case_type resolved from Case.type)
    case_type: str = "generic"                   # Override: determines config directory. If case_id provided, defaults to Case.type
    document_type: str                           # Which document type's fields to extract
    extraction_mode: ExtractionMode = ExtractionMode.REFERENCED
    output_schema: Optional[str] = None          # For direct mode: registered schema name
    infer_references: bool = False               # For direct mode: run reference-inference pass

    # Retriever scope (at least one required)
    document_ids: Optional[list[str]] = None
    page_ids: Optional[list[str]] = None
    file_ids: Optional[list[str]] = None

    # Field selection
    fields: Optional[list[str]] = None
    field_overrides: Optional[list[FieldDefinition]] = None

    reference_granularity: ReferenceGranularity = ReferenceGranularity.FULL
    content_mode: ContentMode = ContentMode.MARKDOWN
```

### 2.6 Extraction Response

```python
class ExtractionResponse(BaseModel):
    """Response from field extraction."""
    document_id: str
    document_type: str
    case_type: str
    extraction_mode: str
    results: dict                                # Referenced: {field_name: FieldResult}
                                                 # Direct: serialized Pydantic model as dict
    reference_annotations: Optional[list[FieldReference]] = None  # Direct mode + infer_references
    model_used: str
    reference_granularity: str
```

Note: In referenced mode, `results` is `dict[str, FieldResult]`. In direct mode, `results` is the Pydantic model serialized via `.model_dump()`. The `extraction_mode` field tells the consumer how to interpret `results`.

---

## 3. Document Classification & Splitting

When a file contains multiple logical documents (e.g., a PDF with several invoices), the extracting engine can classify and split it into segments before extraction.

### 3.1 Split & Classify Models

```python
class SplitSegment(BaseModel):
    """A classified segment within a multi-document file."""
    document_type: str
    page_numbers: list[int]

class SplitClassifyResult(BaseModel):
    """Result of splitting and classifying a document."""
    segments: list[SplitSegment]

class LLMSplitClassifyBatchResult(BaseModel):
    """LLM output for a batch of pages."""
    result: list[SplitSegment]
```

### 3.2 Splitting Strategy

Splitting uses a batched approach for large documents:

1. **Batch pages**: Divide document pages into batches of `batch_size` pages with `overlap_factor` page overlap between consecutive batches
2. **Classify batches**: Send each batch to the LLM with the split/classify prompt
3. **Merge results**: Combine batch results, resolving overlaps by preferring the batch where the boundary is more clearly visible
4. **Create sub-documents**: Optionally create new `Document` records for each segment with the classified `document_type`

### 3.3 Split/Classify Prompt Config

Split/classify operations use the same `PromptConfig` structure (Section 5.1) with additional fields:

```yaml
name: split_classify_invoices
output_schema: split_classify
batch_size: 12              # Pages per LLM call
overlap_factor: 3           # Overlap between batches

sys_prompt_template: |
  You are a document analyst. Identify document boundaries
  and classify each section...

user_prompt_template: |
  Document pages (batch {batch_num} of {total_batches}):
  {context}

  Identify document boundaries and classify each section.

model: gpt-4.1
```

---

## 4. Extraction Pipeline

### 4.1 Pipeline Overview

```
[Input]              [Config]           [Retrieval]          [Extraction]         [Ref Inference]      [Enrichment]         [Output]
 ExtractionRequest -> load configs   -> retrieve context -> LLM extraction  ->  (optional pass 2) -> resolve refs    ->  Response
                      by case_type/     per group           per group            direct mode only     referenced mode
                      document_type
```

When `case_type` is not specified, it defaults to `"generic"`.


### 4.2 Detailed Flow

For each extraction request, the engine executes a graph-based workflow:

#### Step 1: Initialize

- Resolve `case_type`: use `Case.type` if `case_id` is provided, otherwise use the request's `case_type` (default `"generic"`)
- Load configs from `config/extracting/{case_type}/{document_type}/`
- If `extraction_mode = "direct"`, load the output schema from the registry
- Load `FieldDefinition` list for the requested `document_type`
- If `fields` is specified, filter to only those fields
- If `field_overrides` is provided, merge/replace matching field definitions
- Group fields by `group` number
- Load `PromptConfig` for each group

#### Step 2: Per-Group Execution (parallel across groups)

For each group of fields:

**2a. Build Prompt Input**
- Convert `FieldDefinition` list to `FieldPrompt` list (name, description, prompt, value_list)
- Collect field dependencies (`inputs`): fetch previously extracted `FieldResult` values from the database
- Build `PromptInput` containing field prompts and prior field values

**2b. Retrieve Context**
- Use the group's `RetrieverConfig` to select a retriever (Section 6)
- Execute retrieval query using field descriptions as the query
- Return a set of `DocumentPage` objects

**2c. Build Context String**
- For each retrieved page, render content using the requested `content_mode`:
  - `markdown`: Use `page.content_markdown` (with `[short_id]` element references)
  - `html`: Use `page.content_html` (with `id` attribute element references)
- Wrap pages with document/page headers for the LLM:
  ```
  # Document d1
  ## Page 3
  [page content here]
  ```
- Build a mapping of short document IDs (`d1`, `d2`) to actual document IDs

**2d. LLM Call**
- Fill prompt templates with `{fields}`, `{context}`, and any schema instructions
- Call the LLM with structured output matching the group's `output_schema`
- Retry up to `retry_attempts` times on failure
- Parse response into `LLMFieldsResult` (or custom schema)

**2e. Enrich Results**
- If `reference_granularity = "full"`:
  - Parse LLM reference strings (e.g., `"d1:3:p5"`, `"d2:1:t3:2"`)
  - Map short document IDs back to actual IDs
  - Fetch `DocumentElement` data from the database
  - Calculate polygon bounding boxes from element data
  - Build `Reference` objects with polygon coordinates
- If `reference_granularity = "page"`:
  - Parse page numbers from LLM references
  - Build `PageReference` objects (no polygon resolution)
- If `reference_granularity = "none"`:
  - Only extract the `content` value

#### Step 3: Combine Results

- Merge results from all groups into a single `dict[str, FieldResult]` (referenced mode) or a combined dict (direct mode)

#### Step 4: Reference Inference (Direct Mode Only)

When `extraction_mode = "direct"` and `infer_references = True`:

1. Take the direct extraction result from Step 2d
2. Re-retrieve context using the same retriever, but with `content_mode` that includes element annotations (markdown with `[short_id]` or HTML with `id` attributes)
3. Build a prompt containing:
   - The original extracted values (serialized as JSON)
   - The annotated document context
   - Instructions to identify which elements support each extracted value
4. LLM returns `ReferenceInferenceResult` — a list of `FieldReference` with `field_path` pointing to each leaf field and its supporting element references
5. Optionally resolve references to polygons (same as Step 2e enrichment)

#### Step 5: Return Response

- Return `ExtractionResponse` with `results`, `extraction_mode`, and optionally `reference_annotations`

### 4.3 Reference String Format

The LLM produces element references in a structured format:

```
d{doc_short_id}:{page_number}:{element_short_id}
d{doc_short_id}:{page_number}:{table_short_id}:{row_number}
```

Examples:
- `d1:3:p5` — Document 1, page 3, paragraph p5
- `d2:1:t3:2` — Document 2, page 1, table t3, row 2
- `d1:5:kv0` — Document 1, page 5, key-value pair kv0

### 4.4 Polygon Resolution

For `full` reference granularity, element references are resolved to bounding box polygons:

1. Look up the `DocumentElement` by `short_id` within the document's `elements` list
2. Extract `bounding_regions[].polygon` from `element_data`
3. For table row references: extract the specific row's cell polygons and compute their union
4. For key-value pairs: compute union of key and value bounding regions
5. Combine with `DocumentPage.width`, `height`, `unit` for coordinate normalization

```python
def calculate_union_polygon(polygons: list[list[float]]) -> list[float]:
    """Compute bounding box union of multiple polygons."""
    # Returns [min_x, min_y, max_x, min_y, max_x, max_y, min_x, max_y]
```

---

## 5. Prompt Configuration

### 5.1 PromptConfig Model

```python
class RetrieverConfig(BaseModel):
    """Configuration for context retrieval."""
    name: str                                    # Retriever name from registry
    retriever_kwargs: dict = {}                  # Additional retriever arguments

    # Vector retriever settings
    index_name: Optional[str] = None             # MongoDB vector search index name
    embedding_model: Optional[str] = None        # litellm model ID (e.g., "azure/text-embedding-3-large")
    embedding_field: Optional[str] = None        # Document field containing embeddings
    content_field: str = "content_markdown"       # Field to retrieve as context
    top_k: int = 10                              # Number of pages to retrieve
    relevance_score_fn: Optional[str] = None     # e.g., "dotProduct"
    search_type: Optional[str] = None            # e.g., "similarity"

    # Fulltext retriever settings
    search_index: Optional[str] = None           # Atlas Search index name
    search_field: Optional[str] = None           # Field to search (e.g., "content")

class PromptConfig(BaseModel):
    """LLM prompt configuration for field extraction."""
    name: str                                    # Prompt identifier
    case_type: str = "generic"                   # Which case type this applies to
    document_type: Optional[str] = None          # Which document type this applies to
    groups: Optional[list[int]] = None           # Which field groups (None/[0] = default)
    output_schema: str = "default"               # Schema name from registry

    sys_prompt_template: str                     # System prompt (supports {FIELD_SCHEMA} placeholder)
    user_prompt_template: str                    # User prompt (supports {fields}, {context} placeholders)
    model: str = "gpt-4.1"                       # LLM model identifier
    retry_attempts: int = 3
    llm_kwargs: dict = {}                        # Temperature, top_p, etc.

    retriever_config: Optional[RetrieverConfig] = None
    content_mode: ContentMode = ContentMode.MARKDOWN
    reference_granularity: ReferenceGranularity = ReferenceGranularity.FULL

    # Split/classify specific
    batch_size: Optional[int] = None             # Pages per batch
    overlap_factor: Optional[int] = None         # Overlap between batches

    # Versioning
    hash: Optional[str] = None
    version: Optional[int] = None
```

### 5.2 Prompt Template Placeholders

| Placeholder | Description |
|-------------|-------------|
| `{fields}` | Rendered field definitions (names, descriptions, prompts, value lists) |
| `{context}` | Retrieved document/page content |
| `{FIELD_SCHEMA}` | JSON schema description of the expected output format |
| `{batch_num}` | Current batch number (split/classify only) |
| `{total_batches}` | Total number of batches (split/classify only) |

### 5.3 Prompt Resolution

For a given `(document_type, group)` pair, prompt resolution follows this order:

1. Check for a group-specific prompt (where `groups` contains the group number)
2. Fall back to the default prompt (where `groups` is `None` or `[0]`)
3. Raise an error if no prompt matches

---

## 6. Retrieval Modes

The extracting engine supports multiple retrieval strategies for selecting context pages.

### 6.1 Retriever Registry

```python
RETRIEVERS = {
    "vector_retriever": get_vector_retriever,
    "fulltext_retriever": get_fulltext_retriever,
    "pages_retriever": get_pages_retriever,
    # Custom retrievers can be registered at runtime
}
```

### 6.2 Vector Retriever

Uses MongoDB Atlas Vector Search to find semantically relevant pages.

- Generates a query embedding from the field descriptions using `litellm.aembedding()`
- Queries the vector index configured in `RetrieverConfig`
- Pre-filters by `document_id` to scope results to the target documents
- Returns `top_k` most similar pages

```yaml
retriever_config:
  name: vector_retriever
  index_name: vec_pages_large_dot
  embedding_model: azure/text-embedding-3-large
  embedding_field: emb_content_markdown_text_embedding_3_large
  content_field: content_markdown
  top_k: 10
  relevance_score_fn: dotProduct
```

### 6.3 Full-Text Retriever

Uses MongoDB Atlas Search for keyword-based retrieval.

- Queries the Atlas Search index with the field descriptions as search text
- Pre-filters by `document_id`
- Returns `top_k` most relevant pages

```yaml
retriever_config:
  name: fulltext_retriever
  search_index: ft_pages
  search_field: content
  content_field: content_markdown
  top_k: 10
```

### 6.4 Pages Retriever

Directly fetches specific pages by ID. Used when page numbers are already known (e.g., from a prior split/classify step).

- No search — retrieves exact pages from MongoDB
- Useful after document splitting when each segment's pages are known

```yaml
retriever_config:
  name: pages_retriever
  content_field: content_markdown
```

When using the pages retriever, the `RetrieverFilter` on the extraction request supplies the page IDs:

```python
class RetrieverFilter(BaseModel):
    document_ids: Optional[list[str]] = None
    page_ids: Optional[list[str]] = None
```

### 6.5 Custom Retrievers

Custom retriever functions can be registered at runtime. A retriever must implement:

```python
async def custom_retriever(
    query: str,
    retriever_config: RetrieverConfig,
    document_ids: list[str],
    filter: Optional[RetrieverFilter] = None,
) -> list[DocumentPage]:
    """Return relevant pages for the extraction context."""
    ...
```

---

## 7. Content Mode: HTML vs Markdown

The `content_mode` setting controls which content representation is used when building LLM context from retrieved pages.

### 7.1 Markdown Mode (default)

Uses `DocumentPage.content_markdown`. Element references appear as `[short_id]` prefixes:

```markdown
## Page 3

### Paragraphs

[p0] Insurance Policy Agreement
[p1] This policy is effective from January 1, 2025.

### Tables

Table [t0]

| Row # | Coverage | Limit |
| --- | --- | --- |
| 1 | Property | $1,000,000 |

### Key-Value Pairs

[kv0] **Policy Number** = POL-2025-001
```

The LLM references elements using the short_id format: `d1:3:p0`, `d1:3:t0:1`.

### 7.2 HTML Mode

Uses `DocumentPage.content_html`. Element references appear as `id` attributes:

```html
<h2>Page 3</h2>

<h3>Paragraphs</h3>
<p id="p0">Insurance Policy Agreement</p>
<p id="p1">This policy is effective from January 1, 2025.</p>

<h3>Tables</h3>
<table id="t0">
  <thead><tr><th>Row #</th><th>Coverage</th><th>Limit</th></tr></thead>
  <tbody><tr><td>1</td><td>Property</td><td>$1,000,000</td></tr></tbody>
</table>

<h3>Key-Value Pairs</h3>
<div id="kv0"><strong>Policy Number</strong> = POL-2025-001</div>
```

The LLM references elements using the same short_id format regardless of content mode.

---

## 8. Schema & Retriever Registry

### 8.1 Overview

The registry provides a central lookup for output schemas and retriever factories. This enables prompt configs to reference schemas and retrievers by name.

### 8.2 Schema Registry

Maps schema names to Pydantic models. The `"default"` schema is `LLMFieldsResult`.

```python
SCHEMAS: dict[str, type[BaseModel]] = {
    "default": LLMFieldsResult,
    "split_classify": LLMSplitClassifyBatchResult,
    # Custom schemas registered per deployment:
    # "invoice_line_items": LLMLineItemsResult,
}
```

Custom schemas are registered by adding entries:

```python
from mydocs.extracting.registry import SCHEMAS

SCHEMAS["invoice_line_items"] = LLMLineItemsResult
```

### 8.3 Retriever Registry

Maps retriever names to factory functions.

```python
RETRIEVERS: dict[str, Callable] = {
    "vector_retriever": get_vector_retriever,
    "fulltext_retriever": get_fulltext_retriever,
    "pages_retriever": get_pages_retriever,
}
```

---

## 9. Configuration File Layout


### 9.1 Directory Structure

```
config/
  parser.yml
  extracting/
    {case_type}/                              # e.g., generic/, insurance_claim/
      {document_type}/                        # e.g., claim/, policy/, invoice/
        fields/
          {document_type}.yaml
          {document_type}_group_1.yaml
        prompts/
          main.yaml
          group_1.yaml
        field_manifest.yaml
        prompt_manifest.yaml
      split_classify/                         # Case-type level (not document-type)
        prompts/
          {name}.yaml
```

All directory names are lowercase. Case types and document types can be any value in the database, but are always lowercased for config paths and filesystem directories.

**Config fallback**: If a config is not found under `{case_type}/{document_type}/`, the engine falls back to `generic/{document_type}/`.

### 9.2 Field Definition YAML

```yaml
# config/extracting/generic/claim/fields/claim.yaml
- name: DateOfLoss
  description: Date on which the loss event occurred
  data_type: date
  prompt: |
    Extract the date of loss. Return in ISO format 'yyyy-MM-dd'.
    Look for phrases like "date of loss", "loss date", "incident date".

- name: CauseOfLoss
  description: Primary cause of the loss event
  data_type: enum
  prompt: |
    Classify the cause of loss into one of the provided categories.
  value_list:
    - name: Fire
      prompt: Any fire-related damage including smoke damage
    - name: Water Damage
      prompt: Flooding, pipe burst, water intrusion
    - name: Theft
    - name: Natural Disaster

- name: ClaimAmount
  description: Total claimed amount
  data_type: currency
  group: 1
  prompt: |
    Extract the total claim amount. Include currency.
  inputs:
    - field_name: DateOfLoss
```

### 9.3 Prompt YAML

```yaml
# config/extracting/generic/claim/prompts/main.yaml
name: claim_extraction
document_type: claim
output_schema: default

sys_prompt_template: |
  You are a document analysis assistant specializing in insurance claims.
  Extract the requested fields from the provided document context.

  {FIELD_SCHEMA}

  For each field, provide:
  - content: the extracted value
  - justification: why you chose this value
  - citation: exact text from the document
  - references: element references in format d{id}:{page}:{element_id}

user_prompt_template: |
  Fields to extract:
  {fields}

  Document context:
  {context}

model: gpt-4.1
llm_kwargs:
  temperature: 0.3
  top_p: 0.2

retriever_config:
  name: vector_retriever
  index_name: vec_pages_large_dot
  embedding_model: azure/text-embedding-3-large
  embedding_field: emb_content_markdown_text_embedding_3_large
  content_field: content_markdown
  top_k: 10
  relevance_score_fn: dotProduct

retry_attempts: 3
content_mode: markdown
reference_granularity: full
```

---

## 10. Ad-Hoc Field Definitions

The system supports providing custom field definitions at request time, without pre-configuring them in YAML files.

### 10.1 Via API

Pass `field_overrides` in the `ExtractionRequest`:

```json
{
    "document_ids": ["doc_abc123"],
    "document_type": "generic",
    "field_overrides": [
        {
            "name": "CompanyName",
            "description": "Name of the company mentioned in the document",
            "data_type": "string",
            "prompt": "Extract the primary company name from the document header."
        },
        {
            "name": "TotalAmount",
            "description": "Total monetary amount",
            "data_type": "currency"
        }
    ],
    "reference_granularity": "none"
}
```

### 10.2 Behavior

- If `document_type` has pre-configured fields and `fields` is `null`, ad-hoc fields are **appended** to the configured fields
- If `fields` is specified, only those named fields are extracted (from config + overrides)
- Ad-hoc fields use the default prompt for the document type (group 0)
- Ad-hoc fields are not persisted to the configuration system

---

## 11. Custom Pydantic Structure Extraction

For extracting structured data that doesn't fit the flat field model (e.g., line items, nested records), the engine supports custom Pydantic output schemas in both extraction modes.

### 11.1 Referenced Mode (One-Pass)

In referenced mode, custom schemas use `LLMFieldItem` fields so that references are captured inline:

```python
# mydocs/extracting/schemas/invoice.py

class LLMLineItem(BaseModel):
    description: LLMFieldItem
    quantity: LLMFieldItem
    unit_price: LLMFieldItem
    amount: LLMFieldItem

class LLMLineItemsResult(BaseModel):
    result: list[LLMLineItem]
```

Each sub-field within the custom model is an `LLMFieldItem`, which provides `content`, `justification`, `citation`, and `references` for every extracted value.

When enriching results from referenced-mode custom schemas, the engine:

1. Iterates over each item in `result`
2. For each `LLMFieldItem` sub-field, resolves references according to the `reference_granularity`
3. Converts each `LLMFieldItem` to a `FieldResult`
4. Returns a list of dicts (one per item), where each dict maps sub-field names to `FieldResult` objects

### 11.2 Direct Mode (Multi-Pass)

In direct mode, custom schemas use native Python types:

```python
class AmountTableLineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float

class AmountTable(BaseModel):
    line_items: list[AmountTableLineItem]
```

When `infer_references = True`, the reference-inference pass produces `FieldReference` entries with JSONPath-like `field_path` values:
- `"line_items[0].description"`
- `"line_items[0].amount"`
- `"line_items[1].description"` etc.

This flat list of references supports arbitrary nesting depth — each leaf field in the result gets a path-addressable reference annotation.

### 11.3 Registering the Schema

```python
from mydocs.extracting.registry import SCHEMAS
SCHEMAS["invoice_line_items"] = LLMLineItemsResult
```

### 11.4 Prompt Config for Custom Schemas

```yaml
name: invoice_line_items
document_type: invoice
groups: [1]
output_schema: invoice_line_items

sys_prompt_template: |
  Extract all line items from the invoice...

user_prompt_template: |
  Invoice context:
  {context}

  Extract all line items with description, quantity, unit price, and amount.

model: gpt-4.1
```

---

## 12. Database Storage

### 12.1 Collections

| Collection | Model | Description |
|------------|-------|-------------|
| `field_definitions` | `FieldDefinition` | System-managed field definitions (synced from YAML) |
| `prompt_configs` | `PromptConfig` | System-managed prompt configurations (synced from YAML) |
| `field_results` | `FieldResultRecord` | Extracted field values per document |
| `user_field_definitions` | `UserFieldDefinition` | User-created field definitions used as overrides |

```python
class UserFieldDefinition(MongoBaseModel):
    case_type: str = "generic"
    document_type: str
    field: FieldDefinition                       # The field definition
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

    class Settings:
        name = "user_field_definitions"
        composite_key = ["case_type", "document_type", "field.name"]
```

### 12.2 FieldResultRecord

```python
class FieldResultRecord(MongoBaseModel):
    document_id: str
    document_type: str
    field_name: str
    result: FieldResult                          # The extraction output

    class Settings:
        name = "field_results"
        composite_key = ["document_id", "field_name"]
```

The composite key ensures that re-extracting the same field for the same document produces an idempotent upsert.

### 12.3 Versioning

Field definitions and prompt configs support versioning via content hashing:

- On sync from YAML, the content hash is compared against the stored version
- If changed, the version is incremented and a `version_history` list is updated
- This enables tracking which version of prompts/fields produced a given result

---

## 13. Package Structure

```
mydocs/
  extracting/
    __init__.py
    models.py                   # FieldDefinition, FieldResult, LLMFieldItem, etc.
    config.py                   # ExtractingConfig (YAML loading)
    extractor.py                # BaseExtractor with graph-based pipeline
    retrievers.py               # Vector, fulltext, pages retriever factories
    registry.py                 # Schema and retriever registries
    enrichment.py               # Reference resolution, polygon calculation
    splitter.py                 # Document split/classify logic
    prompt_utils.py             # Prompt and field config loading, versioning
    schemas/                    # Custom output schemas
      __init__.py
config/
  extracting/
    {case_type}/
      {document_type}/
        fields/
        prompts/
```

---

## 14. Dependencies

| Package | Purpose |
|---------|---------|
| `langgraph` | Async graph-based workflow orchestration for the extraction pipeline |
| `lightodm` | MongoDB ODM for field results and config storage |
| `litellm` | LLM calls (structured output) and embedding generation |
| `pydantic` | Data models, structured output schemas |
| `pyyaml` | YAML configuration loading |
| `tinystructlog` | Structured logging |

---

## 15. Integration Points

### 15.1 Parsing Engine

- Reads `Document`, `DocumentPage`, `DocumentElement` models
- Uses `content_markdown` and `content_html` page fields for LLM context
- Uses `element_data` for polygon resolution
- Extends `DocumentTypeEnum` with extraction-specific types
- Requires `Case` model update: add `type: str = "generic"` field (see Section 1.1)

### 15.2 Retrieval Engine

- Uses vector search infrastructure (indexes, embeddings) for context retrieval
- Uses `litellm.aembedding()` for query embedding generation
- Uses fulltext search for keyword-based retrieval

### 15.3 Backend API

Future endpoints:

```
POST /api/v1/extract                     # Run field extraction (accepts case_type)
POST /api/v1/split-classify              # Run document splitting (accepts case_type)
GET  /api/v1/cases/{id}/fields           # Get extracted fields for a case
GET  /api/v1/field-definitions/{case_type}/{doc_type}  # List field definitions
```

### 15.4 CLI

Future commands:

```
mydocs extract <doc_id> --type <document_type>    # Extract fields
mydocs split <doc_id>                              # Split/classify document
mydocs fields list --type <document_type>          # List field definitions
mydocs fields show <field_name> --type <type>      # Show field definition details
```
