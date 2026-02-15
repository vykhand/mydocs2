# Extracting Engine

**Package**: `mydocs.extracting`
**Spec**: [docs/specs/extracting-engine.md](specs/extracting-engine.md)

The extracting engine performs LLM-based information extraction from parsed documents. It takes parsed `Document`/`DocumentPage` models, retrieves relevant context, sends it to an LLM with structured output, and returns typed field results with optional source references.

---

## Architecture

```
ExtractionRequest
    │
    ▼
BaseExtractor.run()
    ├── resolve case_type (from Case or request)
    ├── load field definitions (YAML)
    ├── apply field_overrides / field filters
    ├── group fields by group number
    ├── load PromptConfig per group
    │
    └── for each group ── _run_group()
         ├── get_prompt_input()      build FieldPrompt list, resolve dependencies
         ├── retriever_fn()          fetch DocumentPages via registry retriever
         ├── get_context()           render pages into LLM context string
         ├── _call_llm()             litellm.acompletion with structured output
         ├── enrich_field_results()  resolve references → FieldResult
         └── return SubgraphOutput
    │
    ▼
ExtractionResponse
```

> **Spec deviation — sequential group execution**: The spec (Section 4.2) says groups execute **in parallel** via LangGraph `Send()`. The actual code in `extractor.py:141` iterates groups with a **sequential `for` loop**. The LangGraph `Send` import exists but is unused. The graph-based subgraph described in the spec docstring (`START → get_prompt_input → retriever_step → ...`) is not wired up — each step is called directly in `_run_group()`.

---

## Module Reference

### `models.py` — Data Models

All enumerations, field definitions, result models, request/response types, MongoDB records, config models, and pipeline state models. Matches the spec with the following additions:

| Model | Status |
|-------|--------|
| `ReferenceGranularity`, `ContentMode`, `ExtractionMode`, `FieldDataType` | Implemented as specified |
| `FieldValueOption`, `FieldRequirement`, `FieldDefinition` | Implemented as specified |
| `Reference`, `PageReference`, `FieldResult` | Implemented as specified |
| `FieldReference`, `ReferenceInferenceResult` | Implemented as specified (models exist, but the reference inference pass is **not yet wired up** — see below) |
| `LLMFieldItem`, `LLMFieldsResult` | Implemented as specified |
| `SplitSegment`, `SplitClassifyResult`, `LLMSplitClassifyBatchResult` | Implemented as specified |
| `ExtractionRequest`, `ExtractionResponse` | Implemented as specified |
| `FieldResultRecord`, `UserFieldDefinition` | Implemented as specified (MongoDB records via `lightodm`) |
| `RetrieverConfig`, `PromptConfig` | Implemented as specified |
| `FieldPrompt`, `FieldInput`, `PromptInput` | **Code-only** — pipeline-internal models not described in the spec |
| `RetrieverFilter` | Implemented as specified |
| `SubgraphOutput`, `ExtractGroupState`, `ExtractorState` | **Code-only** — LangGraph state models not described in the spec |

> **Spec deviation — `DocumentTypeEnum`**: The spec defines a `DocumentTypeEnum(StrEnum)` that should be extended with domain types. This enum is **not present** in `models.py`; document types are plain strings throughout.

### `extractor.py` — Core Pipeline (`BaseExtractor`)

The `BaseExtractor` class accepts an `ExtractionRequest` and drives the full pipeline.

**`run()`** (line 98):
1. Resolves `case_type` — looks up `Case.type` via `Case.aget()` if `case_id` is provided
2. Loads field definitions via `get_all_fields()`
3. Applies `field_overrides` (replaces fields with matching names, appends new ones)
4. Filters to `request.fields` if specified
5. Groups fields by `field.group`
6. Loads and validates `PromptConfig` per group
7. Iterates groups sequentially, calling `_run_group()` for each
8. Saves results to MongoDB via `FieldResultRecord.asave()`
9. Returns `ExtractionResponse`

**`_run_group()`** (line 180):
1. Builds `PromptInput` with field prompts and resolved dependencies
2. Retrieves context pages via the configured retriever
3. Builds context string with `get_context()`
4. Formats field prompts, fills template placeholders (`{fields}`, `{context}`, `{FIELD_SCHEMA}`)
5. Calls `_call_llm()` with structured output schema
6. Enriches results (referenced mode) or wraps raw results (direct/custom mode)

**`_call_llm()`** (line 271):
- Uses `litellm.acompletion()` with `response_format=output_schema`
- Retries up to `prompt_config.retry_attempts` times
- Parses response via `output_schema.model_validate_json()`

> **Spec deviation — direct mode handling**: For non-`LLMFieldsResult` schemas (direct mode or custom schemas), the code stores each list item as a JSON-serialized `FieldResult` with key `item_{i}` (line 262). The spec describes direct mode returning a serialized Pydantic model dict. The code path is functional but rudimentary.

> **Spec deviation — reference inference not implemented**: The spec's Step 4 (Section 4.2) describes a second LLM pass for direct mode with `infer_references=True`. The `FieldReference` and `ReferenceInferenceResult` models exist, but the inference logic is **not implemented** — `infer_references` is accepted in `ExtractionRequest` and stored in `ExtractorState` but never acted upon.

> **Spec deviation — result saving**: The code saves results to MongoDB after extraction (line 165). The spec does not explicitly describe this as part of the pipeline flow, though it defines `FieldResultRecord`.

### `context.py` — Context Building

**`fields_to_query(fields)`**: Concatenates field names, descriptions, and prompts into a single search query string for retrievers.

**`get_context(pages, content_mode)`**: Renders retrieved pages into an LLM context string. Groups pages by document, assigns short IDs (`d1`, `d2`), and formats as:

```
# Document d1
## Page 3
[page content]
```

Returns `(context_string, doc_short_to_long)` where the mapping converts short IDs back to real document IDs. Selects `content_html` or `content_markdown` based on `content_mode`, with fallback chain: `content_html → content_markdown → content`.

**`fields_to_prompts(fields)`**: Converts `FieldDefinition` → `FieldPrompt` (strips to name, description, prompt, value_list).

**`format_fields_for_prompt(field_prompts)`**: Renders field prompts as a markdown-formatted string for the `{fields}` placeholder. Includes instructions and allowed values when present.

**`get_prompt_input(fields, document_id, document_type)`**: Builds `PromptInput` for a group. Resolves field dependencies (`inputs`) by querying `FieldResultRecord` from MongoDB for previously extracted values.

### `enrichment.py` — Reference Resolution

**`calculate_union_polygon(polygons)`**: Computes bounding box union of multiple polygons. Returns 8-point rectangle `[min_x, min_y, max_x, min_y, max_x, max_y, min_x, max_y]`.

**`parse_reference_string(ref_str)`**: Parses LLM reference strings like `d1:3:p5` or `d1:3:t3:2` via regex. Returns dict with `doc_short_id`, `page_number`, `element_short_id`, and optional `row_number`.

**`resolve_reference(ref_str, doc_short_to_long, documents)`**: Full resolution pipeline: parse reference → find element by `short_id` in document → extract polygon → fetch page dimensions → build `Reference` object.

**`resolve_page_reference(ref_str, doc_short_to_long)`**: Lightweight resolution: parse reference → fetch page → build `PageReference` (no polygon).

**`enrich_field_results(llm_result, doc_short_to_long, reference_granularity, model_name)`**: Batch enrichment of `LLMFieldItem` list. Behavior by granularity:
- `none`: Wraps items as `FieldResult` with content only
- `page`: Resolves `PageReference` objects, deduplicates by `(document_id, page_number)`
- `full`: Resolves full `Reference` objects with polygon data, pre-fetches documents

### `retrievers.py` — Context Retrieval

Four retriever functions, all with the same signature:
```python
async def retriever(query, retriever_config, retriever_filter) -> list[DocumentPage]
```

| Retriever | Registry Key | Description |
|-----------|-------------|-------------|
| `get_vector_retriever` | `vector_retriever` | MongoDB Atlas `$vectorSearch`. Generates query embedding via `litellm.aembedding()`, filters by `document_id`, returns `top_k` pages. |
| `get_fulltext_retriever` | `fulltext_retriever` | MongoDB Atlas Search `$search`. Keyword-based compound query with document ID filtering. |
| `get_document_pages_retriever` | `document_pages_retriever` | Fetches **all** pages for given document IDs, sorted by page number. Ignores the query. |
| `get_pages_retriever` | `pages_retriever` | Fetches specific pages by `page_ids`. Ignores the query. |

> **Spec deviation — extra retriever**: `document_pages_retriever` is **not in the spec**. It fetches all pages for a document (no search). The default `generic/generic` prompt config uses this retriever.

> **Spec deviation — retriever signature**: The spec (Section 6.5) defines the custom retriever signature as `(query, retriever_config, document_ids, filter)`. The actual implementations take `(query, retriever_config, retriever_filter)` — document IDs are accessed via `retriever_filter.document_ids` rather than as a separate parameter.

All retrievers are registered in the `RETRIEVERS` dict at module load time (bottom of `retrievers.py`), and the `__init__.py` imports the module to trigger registration.

### `registry.py` — Schema & Retriever Registries

Two global dicts:

```python
SCHEMAS = {
    "default": LLMFieldsResult,
    "split_classify": LLMSplitClassifyBatchResult,
}

RETRIEVERS = {}  # Populated by retrievers.py on import
```

Lookup functions `get_schema(name)` and `get_retriever(name)` raise `SchemaNotFoundError` / `RetrieverNotFoundError` if the key is not found. Custom schemas can be registered by adding to `SCHEMAS`.

### `prompt_utils.py` — Configuration Loading

**Config path resolution**: `_get_config_dir(case_type, document_type)` resolves to `config/extracting/{case_type}/{document_type}/`, falling back to `config/extracting/generic/{document_type}/` if the primary path doesn't exist.

**`get_all_fields(case_type, document_type)`**: Loads all YAML files from the `fields/` subdirectory. Supports two YAML formats: a top-level list of field dicts, or a dict with a `fields` key.

**`get_field_groups(case_type, document_type)`**: Loads fields and groups them by `field.group` number.

**`get_prompt(case_type, document_type, group)`**: Loads prompt configs from the `prompts/` subdirectory. Resolution order:
1. Group-specific match (prompt where `groups` contains the requested group number)
2. Default prompt (`groups` is `None` or `[0]`)
3. Single-prompt fallback (if only one prompt file exists, use it regardless)
4. Raise `ConfigNotFoundError`

**`validate_prompt_consistency(prompt_config)`**: Warns if `{fields}` or `{context}` are missing from `user_prompt_template`. Returns `False` but does **not** raise.

**`validate_field_consistency(fields, prompt_config)`**: Raises `FieldConsistencyError` if a field's `inputs` reference a field name not in the current field set (unless the dependency specifies a cross-type `document_type`).

> **Spec deviation — no `config.py`**: The spec (Section 13) lists a `config.py` module for `ExtractingConfig` (YAML loading). This module does not exist; its responsibilities are handled by `prompt_utils.py`.

> **Spec deviation — no versioning**: The spec (Section 12.3) describes content hashing and version incrementing on YAML sync. The code has `calculate_content_hash()` and manifest helpers (`load_manifest_file`, `save_manifest_file`) but they are **not called** anywhere. `PromptConfig.hash` and `PromptConfig.version` fields exist but are never populated.

### `splitter.py` — Document Classification & Splitting

**`batch_pages_with_overlap(pages, batch_size, overlap_factor)`**: Divides pages into overlapping batches with configurable size and overlap.

**`run_llm_split_classify(context, prompt_config, batch_num, total_batches)`**: Sends a page batch to the LLM with `{context}`, `{batch_num}`, `{total_batches}` template variables. Uses `LLMSplitClassifyBatchResult` as structured output.

**`combine_overlapping_results(batch_results, batches)`**: Merges overlapping batch results. For pages classified in multiple batches, prefers the classification from the batch where the page is more centrally positioned (not at the boundary). Produces contiguous `SplitSegment` list.

**`split_and_classify(document_id, prompt_config, content_mode)`**: Main entry point. Fetches all pages for a document, batches them, classifies each batch via LLM, and merges results. Returns `SplitClassifyResult`.

> **Spec deviation — no sub-document creation**: The spec (Section 3.2, step 4) mentions optionally creating new `Document` records for each segment. This is not implemented; the function returns segments but does not persist them.

### `exceptions.py` — Exception Hierarchy

```
ExtractionError (base)
├── NoDocumentsFoundError
├── FieldConsistencyError
├── ConfigNotFoundError
├── SchemaNotFoundError
└── RetrieverNotFoundError
```

### `schemas/` — Custom Output Schemas

Empty `__init__.py`. No custom schemas are registered. The spec describes example schemas like `LLMLineItemsResult` for invoice line items, but none are implemented.

---

## Configuration

### Directory Layout

```
config/
  extracting/
    generic/
      generic/
        fields/
          main.yaml          # Default field definitions
        prompts/
          main.yaml          # Default prompt config
```

The spec describes a richer layout with per-document-type directories, group-specific files, manifests, and split/classify configs. Only the `generic/generic` path exists with a single field and prompt.

### Default Field (`config/extracting/generic/generic/fields/main.yaml`)

One field defined: `summary` (data_type: `text`, group: `0`) — extracts a concise document summary.

### Default Prompt (`config/extracting/generic/generic/prompts/main.yaml`)

- **Model**: `azure/gpt-4.1`
- **Retriever**: `document_pages_retriever` (fetches all pages, no search)
- **Reference granularity**: `none` (content only, no polygon/page references)
- **LLM kwargs**: `temperature: 0.3`, `top_p: 0.2`
- **Output schema**: `default` (`LLMFieldsResult`)

---

## Spec Deviations Summary

| Area | Spec | Code | Impact |
|------|------|------|--------|
| Group execution | Parallel via LangGraph `Send()` | Sequential `for` loop | Performance (no parallelism) |
| LangGraph graph | Subgraph wired as `START → steps → END` | Steps called directly in `_run_group()` | Structural (works, but not graph-based) |
| `DocumentTypeEnum` | StrEnum in models | Not implemented; plain strings | No type safety on document types |
| Direct mode enrichment | Custom schema results as native dict | Stored as JSON-serialized `item_{i}` keys | API shape differs from spec |
| Reference inference | Second LLM pass for direct mode | Not implemented (models exist, logic missing) | Feature gap |
| Config versioning | Hash + version tracking on YAML sync | Hash helpers exist, never called | Feature gap |
| Sub-document creation | Splitter creates Document records | Not implemented | Feature gap |
| `config.py` module | `ExtractingConfig` YAML loading class | Does not exist; `prompt_utils.py` handles it | Naming difference |
| `document_pages_retriever` | Not in spec | Implemented and used as default | Extra retriever |
| Retriever signature | `(query, config, document_ids, filter)` | `(query, config, retriever_filter)` | Signature difference |
| Pipeline state models | Not in spec | `FieldPrompt`, `FieldInput`, `PromptInput`, `ExtractGroupState`, `ExtractorState`, `SubgraphOutput` | Implementation detail |
| `NoDocumentsFoundError` | Not in spec | Defined but unused | Dead code |

---

## Dependencies

| Package | Usage |
|---------|-------|
| `litellm` | LLM calls (`acompletion` with structured output) and embeddings (`aembedding`) |
| `langgraph` | Imported (`Send`, `StateGraph`, `START`, `END`) but **not actively used** for orchestration |
| `lightodm` | MongoDB ODM (`MongoBaseModel`) for `FieldResultRecord`, `UserFieldDefinition` |
| `pydantic` | All data models |
| `pyyaml` | YAML config loading |
| `tinystructlog` | Structured logging throughout |
