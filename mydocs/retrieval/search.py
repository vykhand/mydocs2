"""Search orchestrator — main entry point for the retrieval engine."""

import asyncio

from tinystructlog import get_logger

from mydocs.parsing.config import ParserConfig
from mydocs.retrieval import embeddings
from mydocs.retrieval import fulltext_retriever
from mydocs.retrieval import hybrid
from mydocs.retrieval import vector_retriever
from mydocs.retrieval.models import SearchRequest, SearchResponse, SearchResult

log = get_logger(__name__)

# Maps (search_target, vector_field) -> index name
VECTOR_INDEX_MAP = {
    ("pages", "emb_content_markdown_text_embedding_3_large"): "vec_pages_large_dot",
}


def _resolve_vector_index(request: SearchRequest) -> tuple[str, str, str]:
    """Resolve the vector index name, vector field, and embedding model.

    Returns (index_name, vector_field, embedding_model).
    """
    parser_config = ParserConfig()

    if request.search_target == "pages":
        emb_configs = parser_config.page_embeddings or []
    else:
        emb_configs = parser_config.document_embeddings or []

    # If index_name is explicitly set, find matching config or use defaults
    if request.vector.index_name:
        index_name = request.vector.index_name
        # Try to find the embedding config that matches this index
        for ec in emb_configs:
            key = (request.search_target, ec.target_field)
            if VECTOR_INDEX_MAP.get(key) == index_name:
                vector_field = ec.target_field
                model = request.vector.embedding_model or ec.model
                return index_name, vector_field, model
        # Fallback: use first config or defaults
        if emb_configs:
            ec = emb_configs[0]
            model = request.vector.embedding_model or ec.model
            return index_name, ec.target_field, model
        model = request.vector.embedding_model or "text-embedding-3-large"
        return index_name, "emb_content_markdown_text_embedding_3_large", model

    # Auto-resolve: use first embedding config
    if not emb_configs:
        raise ValueError(
            f"No embedding configs found for search_target={request.search_target} "
            "and no vector.index_name specified"
        )

    ec = emb_configs[0]
    key = (request.search_target, ec.target_field)
    index_name = VECTOR_INDEX_MAP.get(key)
    if not index_name:
        raise ValueError(
            f"No vector index found for ({request.search_target}, {ec.target_field}). "
            f"Known indexes: {list(VECTOR_INDEX_MAP.keys())}"
        )

    model = request.vector.embedding_model or ec.model
    return index_name, ec.target_field, model


async def search(request: SearchRequest) -> SearchResponse:
    """Execute a search request and return results."""
    log.info(
        "search started",
        query=request.query,
        target=request.search_target,
        mode=request.search_mode,
    )

    needs_fulltext = request.search_mode in ("fulltext", "hybrid")
    needs_vector = request.search_mode in ("vector", "hybrid")

    index_name = None
    embedding_model = None
    query_embedding = None
    vector_field = None

    # Resolve vector index and generate embedding if needed
    if needs_vector:
        index_name, vector_field, embedding_model = _resolve_vector_index(request)
        log.debug(
            "vector index resolved",
            index_name=index_name,
            vector_field=vector_field,
            embedding_model=embedding_model,
        )
        query_embedding = await embeddings.generate_query_embedding(
            request.query, embedding_model
        )

    # Execute searches
    if request.search_mode == "hybrid":
        ft_task = fulltext_retriever.fulltext_search(
            query=request.query,
            search_target=request.search_target,
            fulltext_config=request.fulltext,
            filters=request.filters,
            top_k=request.top_k,
        )
        vec_task = vector_retriever.vector_search(
            query_embedding=query_embedding,
            search_target=request.search_target,
            index_name=index_name,
            vector_field=vector_field,
            filters=request.filters,
            num_candidates=request.vector.num_candidates,
            top_k=request.top_k,
        )
        ft_results, vec_results = await asyncio.gather(ft_task, vec_task)

        combined = hybrid.combine_results(
            ft_results=ft_results,
            vec_results=vec_results,
            hybrid_config=request.hybrid,
            ft_boost=request.fulltext.score_boost,
            vec_boost=request.vector.score_boost,
        )

    elif request.search_mode == "fulltext":
        ft_results = await fulltext_retriever.fulltext_search(
            query=request.query,
            search_target=request.search_target,
            fulltext_config=request.fulltext,
            filters=request.filters,
            top_k=request.top_k,
        )
        combined = []
        for r in ft_results:
            r["scores"] = {"fulltext": r.get("score", 0.0), "vector": 0.0}
            combined.append(r)

    elif request.search_mode == "vector":
        vec_results = await vector_retriever.vector_search(
            query_embedding=query_embedding,
            search_target=request.search_target,
            index_name=index_name,
            vector_field=vector_field,
            filters=request.filters,
            num_candidates=request.vector.num_candidates,
            top_k=request.top_k,
        )
        combined = []
        for r in vec_results:
            r["scores"] = {"fulltext": 0.0, "vector": r.get("score", 0.0)}
            combined.append(r)

    else:
        raise ValueError(f"Unknown search_mode: {request.search_mode}")

    # Post-processing: min_score filter
    if request.min_score > 0:
        combined = [r for r in combined if r["score"] >= request.min_score]

    # Truncate to top_k
    combined = combined[: request.top_k]

    # Filter content fields
    allowed_fields = set(request.include_content_fields)
    for r in combined:
        if "content" not in allowed_fields:
            r["content"] = None
        if "content_markdown" not in allowed_fields:
            r["content_markdown"] = None

    # Build response
    results = [SearchResult(**r) for r in combined]

    response = SearchResponse(
        results=results,
        total=len(results),
        search_target=request.search_target,
        search_mode=request.search_mode,
        vector_index_used=index_name,
        embedding_model_used=embedding_model,
    )

    log.info("search completed", total=response.total)
    return response
