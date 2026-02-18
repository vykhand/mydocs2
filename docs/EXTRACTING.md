# Extracting Engine

**Package**: `mydocs.extracting`
**Spec**: [docs/specs/extracting-engine.md](specs/extracting-engine.md)

The extracting engine performs LLM-based information extraction from parsed documents. It takes parsed `Document`/`DocumentPage` models, retrieves relevant context, sends it to an LLM with structured output, and returns typed field results with optional source references.

Key features:
- **SubDocuments**: Split/classify persists classified segments as `SubDocument` objects on the parent `Document`
- **Case Type Config**: Per-case-type configuration via `case_type.yaml` (split/classify enablement, document types)
- **Target Object Registry**: `(case_type, document_type)` → `MongoBaseModel` mapping for domain-specific extraction targets
- **Subdocument Scoping**: Extraction can be scoped to a specific subdocument, overriding document_type and page_ids
- **Type Coercion**: Target object fields are automatically coerced from `FieldResult` to plain types (`str`, `int`, etc.)

---

## Architecture

```
ExtractionRequest
    │
    ▼
BaseExtractor.run()
    ├── resolve case_type (from Case or request)
    ├── resolve subdocument (if subdocument_id provided)
    │     └── override document_type + page_ids from SubDocument
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
    ├── _save_results()              persist FieldResultRecord (with subdocument_id, case_type)
    ├── _save_target_object()        populate + save target object (if registered)
    │
    ▼
ExtractionResponse (includes subdocument_id, target_object_id)
```

> **Spec deviation — sequential group execution**: The spec (Section 4.2) says groups execute **in parallel** via LangGraph `Send()`. The actual code in `extractor.py` iterates groups with a **sequential `for` loop**. The LangGraph `Send` import exists but is unused. The graph-based subgraph described in the spec docstring (`START → get_prompt_input → retriever_step → ...`) is not wired up — each step is called directly in `_run_group()`.

---

## Module Reference

### `models.py` — Data Models

All enumerations, field definitions, result models, request/response types, MongoDB records, config models, and pipeline state models.

| Model | Status |
|-------|--------|
| `ReferenceGranularity`, `ContentMode`, `ExtractionMode`, `FieldDataType` | Implemented as specified |
| `FieldValueOption`, `FieldRequirement`, `FieldDefinition` | Implemented as specified |
| `Reference`, `PageReference`, `FieldResult` | Implemented as specified |
| `FieldReference`, `ReferenceInferenceResult` | Implemented as specified (models exist, but the reference inference pass is **not yet wired up** — see below) |
| `LLMFieldItem`, `LLMFieldsResult` | Implemented as specified |
| `SplitSegment`, `SplitClassifyResult`, `LLMSplitClassifyBatchResult` | Implemented as specified. `SplitClassifyResult` now includes `subdocuments` field |
| `ExtractionRequest`, `ExtractionResponse` | Implemented with `subdocument_id` and `target_object_id` fields |
| `FieldResultRecord`, `UserFieldDefinition` | Implemented with `subdocument_id` and `case_type` on `FieldResultRecord`. Composite key: `[document_id, subdocument_id, field_name]` |
| `RetrieverConfig`, `PromptConfig` | Implemented as specified |
| `DocumentTypeConfig`, `SplitClassifyConfig`, `CaseTypeConfig` | **New** — case type configuration models for split/classify enablement and document type definitions |
| `FieldPrompt`, `FieldInput`, `PromptInput` | **Code-only** — pipeline-internal models not described in the spec |
| `RetrieverFilter` | Implemented as specified |
| `SubgraphOutput`, `ExtractGroupState`, `ExtractorState` | **Code-only** — LangGraph state models. `ExtractorState` includes `subdocument_id` |

**`mydocs/models.py`** (canonical models) now includes:

| Model | Description |
|-------|-------------|
| `SubDocumentPageRef` | Reference to a single page within a sub-document (document_id, page_id, page_number) |
| `SubDocument` | A classified segment embedded on `Document` — id, case_type, document_type, page_refs |
| `Document.subdocuments` | New optional field: `Optional[List[SubDocument]]` |

> **Spec deviation — `DocumentTypeEnum`**: The spec defines a `DocumentTypeEnum(StrEnum)` that should be extended with domain types. This enum is **not present** in `models.py`; document types are plain strings throughout.

### `extractor.py` — Core Pipeline (`BaseExtractor`)

The `BaseExtractor` class accepts an `ExtractionRequest` and drives the full pipeline.

**`run()`**:
1. Resolves `case_type` — looks up `Case.type` via `Case.aget()` if `case_id` is provided
2. Resolves subdocument — if `subdocument_id` is provided, finds the matching `SubDocument` on the `Document`, overrides `document_type` and `case_type` from it, and scopes `page_ids` to the subdocument's pages
3. Loads field definitions via `get_all_fields()`
4. Applies `field_overrides` (replaces fields with matching names, appends new ones)
5. Filters to `request.fields` if specified
6. Groups fields by `field.group`
7. Loads and validates `PromptConfig` per group
8. Iterates groups sequentially, calling `_run_group()` for each
9. Saves results to MongoDB via `FieldResultRecord.asave()` (with `subdocument_id` and `case_type`)
10. Saves target object via `_save_target_object()` (if a target class is registered)
11. Returns `ExtractionResponse` (with `subdocument_id` and `target_object_id`)

**`_run_group()`** (line 180):
1. Builds `PromptInput` with field prompts and resolved dependencies
2. Retrieves context pages via the configured retriever
3. Builds context string with `get_context()`
4. Formats field prompts, fills template placeholders (`{fields}`, `{context}`, `{FIELD_SCHEMA}`)
5. Calls `_call_llm()` with structured output schema
6. Enriches results (referenced mode) or wraps raw results (direct/custom mode)

**`_call_llm()`** (line 271):
- Uses `litellm.acompletion()` with `response_format=output_schema`
- Two-level retry strategy:
  - **Transport retries** (`transport_retries`): Passed to litellm as `num_retries` for HTTP 429/500/503, connection errors, and timeouts. Managed internally by litellm with exponential backoff. Transport errors (`litellm.exceptions.APIError`) are re-raised immediately since litellm has already exhausted its retries.
  - **Validation retries** (`validation_retries`): Outer loop retries when the LLM returns JSON that fails Pydantic `model_validate_json()`. Rare with `json_schema` structured output but kept as a safety net.
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

**`get_prompt_input(fields, document_id, document_type, subdocument_id="")`**: Builds `PromptInput` for a group. Resolves field dependencies (`inputs`) by querying `FieldResultRecord` from MongoDB for previously extracted values, scoped by `subdocument_id`.

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

### `registry.py` — Schema, Retriever & Target Object Registries

Three global dicts:

- **`SCHEMAS`**: Maps schema names to Pydantic output models (`"default"` → `LLMFieldsResult`, `"split_classify"` → `LLMSplitClassifyBatchResult`)
- **`RETRIEVERS`**: Maps retriever names to async functions. Populated by `retrievers.py` on import.
- **`TARGET_OBJECTS`**: Maps `(case_type, document_type)` tuples to `MongoBaseModel` subclasses. Populated by `case_types/` subpackages on import.

Lookup functions: `get_schema(name)`, `get_retriever(name)`, `get_target_object_class(case_type, document_type)`. Registration: `register_target_object(case_type, document_type, model_class)`.

### `prompt_utils.py` — Configuration Loading

**Config path resolution**: `_get_config_dir(case_type, document_type)` resolves to `config/extracting/{case_type}/{document_type}/`, falling back to `config/extracting/generic/{document_type}/` if the primary path doesn't exist.

**`load_case_type_config(case_type)`**: Loads `CaseTypeConfig` from `config/extracting/{case_type}/case_type.yaml`. Returns a default `CaseTypeConfig` if the file does not exist.

**`get_split_classify_prompt(case_type, prompt_name)`**: Loads the split-classify `PromptConfig` from `config/extracting/{case_type}/split_classify/prompts/{prompt_name}.yaml`. Falls back to generic if not found for the given case type.

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

> **Spec deviation — no versioning**: The spec (Section 12.4) describes content hashing and version incrementing on YAML sync. The code has `calculate_content_hash()` and manifest helpers (`load_manifest_file`, `save_manifest_file`) but they are **not called** anywhere. `PromptConfig.hash` and `PromptConfig.version` fields exist but are never populated.

### `splitter.py` — Document Classification & Splitting

**`batch_pages_with_overlap(pages, batch_size, overlap_factor)`**: Divides pages into overlapping batches with configurable size and overlap.

**`run_llm_split_classify(context, prompt_config, batch_num, total_batches)`**: Sends a page batch to the LLM with `{context}`, `{batch_num}`, `{total_batches}` template variables. Uses `LLMSplitClassifyBatchResult` as structured output. Uses the same two-level retry strategy as `_call_llm()` (transport retries via `transport_retries`, validation retries via `validation_retries` loop).

**`combine_overlapping_results(batch_results, batches)`**: Merges overlapping batch results. For pages classified in multiple batches, prefers the classification from the batch where the page is more centrally positioned (not at the boundary). Produces contiguous `SplitSegment` list.

**`split_and_classify(document_id, prompt_config, content_mode, case_type)`**: Main entry point. Fetches all pages for a document, batches them, classifies each batch via LLM, and merges results. After merging, builds `SubDocument` objects with deterministic IDs and persists them on the parent `Document`. Returns `SplitClassifyResult` with both `segments` and `subdocuments`.

### `exceptions.py` — Exception Hierarchy

```
ExtractionError (base)
├── NoDocumentsFoundError
├── FieldConsistencyError
├── ConfigNotFoundError
├── SchemaNotFoundError
└── RetrieverNotFoundError
```

### `target_objects.py` — Type Coercion and Target Object Population

**`get_inner_type(annotation)`**: Unwraps `Optional[X]` to `X`.

**`coerce_field_result(field_result, target_type)`**: Coerces a `FieldResult` to the target type:
- `FieldResult` → `FieldResult`: pass-through
- `FieldResult` → `str`: returns `.content`
- `FieldResult` → `int`: `int(.content)`
- `FieldResult` → `float`: `float(.content)`
- `FieldResult` → `bool`: boolean evaluation of `.content`

**`populate_target_object(target_obj, field_results)`**: Iterates over target model fields, matches by name against `field_results`, coerces values, and sets attributes. Skips internal fields (`id`, `document_id`, `subdocument_id`, `case_id`).

### `case_types/` — Case Type Subpackages

Each case type has its own subpackage that registers target objects on import:

```
case_types/
  __init__.py          # Imports all case_type packages
  generic/
    __init__.py        # No target objects for generic
```

To add a new case type (e.g., `insurance`):
1. Create `case_types/insurance/__init__.py` — registers target objects via `register_target_object()`
2. Create `case_types/insurance/models.py` — defines `MongoBaseModel` subclasses
3. Add import to `case_types/__init__.py`

The `extracting/__init__.py` imports `case_types` alongside `retrievers` to trigger registration at package import time.

### `schemas/` — Custom Output Schemas

Empty `__init__.py`. No custom schemas are registered. The spec describes example schemas like `LLMLineItemsResult` for invoice line items, but none are implemented.

---

## Configuration

### Directory Layout

```
config/
  extracting/
    generic/
      case_type.yaml           # CaseTypeConfig (split_classify.enabled: false)
      generic/
        fields/
          main.yaml            # Default field definitions
        prompts/
          main.yaml            # Default prompt config
      split_classify/          # Placeholder (disabled for generic)
        prompts/
    {other_case_type}/         # Future case types follow same pattern
      case_type.yaml
      split_classify/
        prompts/
          main.yaml            # Split-classify prompt config
      {document_type}/
        fields/
        prompts/
```

The `case_type.yaml` defines per-case-type settings including split/classify enablement and document type list. The split-classify endpoint checks `case_type.yaml` before proceeding.

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
| Reference inference | Second LLM pass for direct mode | Not implemented (models exist, logic missing) | Feature gap (explicitly out of scope) |
| Config versioning | Hash + version tracking on YAML sync | Hash helpers exist, never called | Feature gap |
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
