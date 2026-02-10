# Retrieval Engine Specification

**Package**: `mydocs.retrieval`
**Version**: 1.0
**Status**: Draft

**Related Specs**: [parsing-engine.md](parsing-engine.md) (data models, ODM layer), [backend.md](backend.md) (HTTP API), [migrations.md](migrations.md) (index setup)

---

## 1. Overview

The retrieval engine provides search and retrieval capabilities over parsed documents and pages. It supports full-text search, vector (semantic) search, and hybrid search combining both approaches.

The retrieval engine operates on the data models defined in [parsing-engine.md](parsing-engine.md) (`Document`, `DocumentPage`) and exposes its functionality as internal Python functions consumed by the [backend](backend.md) API layer and [CLI](cli.md).

---

## 2. Full-Text Search

MongoDB Atlas full-text search indices on:
- `documents.content` -- Search across entire document text
- `pages.content` -- Search within individual pages

Full-text search enables:
- Keyword and phrase search across all ingested documents
- Relevance-ranked results
- Filtering by document tags, file type, status, etc.

### 2.1 Atlas Search Index Definitions

Index on the `documents` collection (`ft_documents`):
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

Index on the `pages` collection (`ft_pages`):
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

---

## 3. Vector Search

Vector embeddings are generated for semantic search using the `litellm` library, which provides a unified interface to multiple embedding providers (OpenAI, Azure OpenAI, Cohere, etc.).

### 3.1 Embedding Configuration

```python
class EmbeddingConfig(BaseModel):
    model: str = "text-embedding-3-large"       # litellm model identifier
    field_to_embed: str = "content_markdown"     # Source field for embedding
    target_field: str                            # Field name to store the vector
                                                 # Convention: emb_{field}_{model_slug}
    dimensions: int = 3072                       # Vector dimensions
```

`EmbeddingConfig` is defined in the parsing engine's configuration (`ParserConfig.page_embeddings`, `ParserConfig.document_embeddings`). See [parsing-engine.md](parsing-engine.md) Section 7.

### 3.2 Embedding Generation

Embeddings are generated using `litellm.aembedding()`:

```python
import litellm

# litellm reads AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_BASE, AZURE_OPENAI_API_VERSION from env
response = await litellm.aembedding(
    model="azure/text-embedding-3-large",
    input=[text_to_embed],
)
vector = response.data[0]["embedding"]
```

This approach:
- Supports 100+ embedding providers through litellm's unified API
- Provides async support via `aembedding()`
- Uses litellm's built-in Azure OpenAI support (`azure/` model prefix)
- Returns standard OpenAI-compatible embedding response format

### 3.3 Vector Index Definition

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

### 3.4 Retrieval Patterns

Two retriever patterns are supported:

1. **Vector Retriever**: Uses MongoDB Atlas Vector Search aggregation pipeline with `$vectorSearch` stage and pre-filtering by `document_id` to find semantically similar pages. Embedding queries are generated via `litellm.aembedding()`.

2. **Pages Retriever**: Directly fetches specific pages by ID using `DocumentPage.afind()` (used when page numbers are known, e.g., from split/classify results).

Both return pages with their `content_markdown` (or configurable content field) for use as LLM context.

---

## 4. Hybrid Search

When `search_mode` = `"hybrid"`, the search executes both full-text and vector searches, then combines results:

1. Run full-text search via Atlas Search `$search` aggregation stage
2. Run vector search via Atlas Vector Search `$vectorSearch` aggregation stage
3. Normalize scores from each search to [0, 1] range
4. Combine using the configured `combination_method`:
   - **RRF** (`"rrf"`): `score = Σ 1/(rrf_k + rank_i)` across search methods. Robust to score distribution differences.
   - **Weighted Sum** (`"weighted_sum"`): `score = w_ft * score_ft + w_vec * score_vec`. Requires score normalization for meaningful combination.
5. Deduplicate results by ID, keeping the highest combined score
6. Sort by combined score descending, apply `min_score` filter, truncate to `top_k`

---

## 5. Search Request/Response Models

These are internal Pydantic models used by the retrieval engine. The HTTP API layer in [backend.md](backend.md) wraps these for REST access.

### 5.1 Search Request

```python
class FuzzyConfig(BaseModel):
    enabled: bool = False
    max_edits: int = 2
    prefix_length: int = 3

class FullTextSearchConfig(BaseModel):
    enabled: bool = True
    content_field: str = "content"
    fuzzy: FuzzyConfig = FuzzyConfig()
    score_boost: float = 1.0

class VectorSearchConfig(BaseModel):
    enabled: bool = True
    index_name: Optional[str] = None
    embedding_model: Optional[str] = None
    num_candidates: int = 100
    score_boost: float = 1.0

class HybridSearchConfig(BaseModel):
    combination_method: str = "rrf"  # "rrf" or "weighted_sum"
    rrf_k: int = 60
    weights: dict = {"fulltext": 0.5, "vector": 0.5}

class SearchFilters(BaseModel):
    tags: Optional[list[str]] = None
    file_type: Optional[str] = None
    document_ids: Optional[list[str]] = None
    status: Optional[str] = None
    document_type: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    search_target: str = "pages"       # "pages" or "documents"
    search_mode: str = "hybrid"        # "fulltext", "vector", or "hybrid"
    fulltext: FullTextSearchConfig = FullTextSearchConfig()
    vector: VectorSearchConfig = VectorSearchConfig()
    hybrid: HybridSearchConfig = HybridSearchConfig()
    filters: SearchFilters = SearchFilters()
    top_k: int = 10
    min_score: float = 0.0
    include_content_fields: list[str] = ["content"]
```

### 5.2 Search Response

```python
class SearchResult(BaseModel):
    id: str
    document_id: str
    page_number: Optional[int] = None
    score: float
    scores: dict  # {"fulltext": float, "vector": float}
    content: Optional[str] = None
    content_markdown: Optional[str] = None
    file_name: Optional[str] = None
    tags: list[str] = []

class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    search_target: str
    search_mode: str
    vector_index_used: Optional[str] = None
    embedding_model_used: Optional[str] = None
```

### 5.3 Search Target Behavior

When `search_target` = `"pages"`:
- Full-text search queries the `pages.content` field (Atlas Search index: `ft_pages`)
- Vector search queries page embedding fields (Atlas Vector Search index selected by `vector.index_name`)
- Filters on `document_ids`, `tags`, `file_type`, `status` are applied via a join/lookup against the parent `documents` collection
- Results include `page_number` and `document_id`

When `search_target` = `"documents"`:
- Full-text search queries the `documents.content` field (Atlas Search index: `ft_documents`)
- Vector search queries document embedding fields (requires a document-level vector index)
- Filters are applied directly on the `documents` collection
- Results do not include `page_number`

### 5.4 Vector Index Selection

When multiple vector indices exist (e.g., different embedding models or dimensions), the index is selected as follows:

1. If `vector.index_name` is specified, use that index directly
2. Otherwise, select the first matching index for the `search_target` collection from the parser configuration (`page_embeddings` or `document_embeddings`)
3. The `embedding_model` for query embedding is determined from the index's associated `EmbeddingConfig`
4. If `vector.embedding_model` is explicitly set, it overrides the inferred model (useful for cross-model experimentation)

---

## 6. Search Indexes

All search indexes are created via the [migration system](migrations.md).

### 6.1 Atlas Search Indexes

| Index Name | Collection | Description |
|------------|------------|-------------|
| `ft_documents` | `documents` | Full-text search on `documents.content` |
| `ft_pages` | `pages` | Full-text search on `pages.content` |

### 6.2 Atlas Vector Search Indexes

| Index Name | Collection | Description |
|------------|------------|-------------|
| `vec_pages_large_dot` | `pages` | Vector search on page embeddings (`emb_content_markdown_text_embedding_3_large`) |

---

## 7. Package Structure

```
mydocs/
  retrieval/
    __init__.py
    search.py                   # Search orchestration (fulltext, vector, hybrid)
    models.py                   # SearchRequest, SearchResponse, SearchResult
    embeddings.py               # Embedding generation via litellm
    vector_retriever.py         # Vector search via $vectorSearch
    fulltext_retriever.py       # Full-text search via $search
    hybrid.py                   # Hybrid combination (RRF, weighted sum)
```

---

## 8. Dependencies

| Package | Purpose |
|---------|---------|
| `lightodm` | MongoDB ODM for aggregation pipelines |
| `litellm` | Unified embedding API |
| `pydantic` | Search request/response models |
