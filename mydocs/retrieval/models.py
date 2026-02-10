"""Search request and response models for the retrieval engine."""

from typing import Optional

from pydantic import BaseModel


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
    search_target: str = "pages"  # "pages" or "documents"
    search_mode: str = "hybrid"  # "fulltext", "vector", or "hybrid"
    fulltext: FullTextSearchConfig = FullTextSearchConfig()
    vector: VectorSearchConfig = VectorSearchConfig()
    hybrid: HybridSearchConfig = HybridSearchConfig()
    filters: SearchFilters = SearchFilters()
    top_k: int = 10
    min_score: float = 0.0
    include_content_fields: list[str] = ["content"]


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
