"""Retriever functions for extraction context selection.

Plain async functions (no LangChain) that return lists of DocumentPage objects.
Uses litellm for embeddings and direct MongoDB aggregation for search.
"""

from typing import Optional

import litellm
from tinystructlog import get_logger

from mydocs.extracting.models import RetrieverConfig, RetrieverFilter
from mydocs.extracting.registry import RETRIEVERS
from mydocs.models import DocumentPage

log = get_logger(__name__)


async def get_vector_retriever(
    query: str,
    retriever_config: RetrieverConfig,
    retriever_filter: Optional[RetrieverFilter] = None,
) -> list[DocumentPage]:
    """Retrieve pages via MongoDB Atlas $vectorSearch.

    Generates a query embedding using litellm.aembedding(), then runs
    a $vectorSearch aggregation pipeline on the pages collection.
    """
    if not retriever_config.embedding_model:
        raise ValueError("embedding_model required for vector retriever")
    if not retriever_config.index_name:
        raise ValueError("index_name required for vector retriever")
    if not retriever_config.embedding_field:
        raise ValueError("embedding_field required for vector retriever")

    # Generate query embedding
    log.debug(f"Generating embedding for vector retrieval, model={retriever_config.embedding_model}")
    response = await litellm.aembedding(
        model=retriever_config.embedding_model,
        input=[query],
    )
    query_embedding = response.data[0]["embedding"]

    # Build $vectorSearch pipeline
    vector_stage: dict = {
        "$vectorSearch": {
            "index": retriever_config.index_name,
            "path": retriever_config.embedding_field,
            "queryVector": query_embedding,
            "numCandidates": retriever_config.top_k * 10,
            "limit": retriever_config.top_k,
        }
    }

    # Pre-filter by document_ids
    if retriever_filter and retriever_filter.document_ids:
        vector_stage["$vectorSearch"]["filter"] = {
            "document_id": {"$in": retriever_filter.document_ids}
        }

    pipeline: list[dict] = [
        vector_stage,
        {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
        {
            "$project": {
                "_id": 1,
                "document_id": 1,
                "page_number": 1,
                "content": 1,
                "content_markdown": 1,
                "content_html": 1,
                "height": 1,
                "width": 1,
                "unit": 1,
                "score": 1,
            }
        },
    ]

    log.debug(f"Vector retriever pipeline: {pipeline}")
    raw = await DocumentPage.aaggregate(pipeline)

    pages = []
    for doc in raw:
        page = DocumentPage(
            document_id=str(doc.get("document_id", "")),
            page_number=doc.get("page_number", 0),
            content=doc.get("content"),
            content_markdown=doc.get("content_markdown"),
            content_html=doc.get("content_html"),
            height=doc.get("height"),
            width=doc.get("width"),
            unit=doc.get("unit"),
        )
        page.id = str(doc["_id"])
        pages.append(page)

    log.info(f"Vector retriever returned {len(pages)} pages")
    return pages


async def get_fulltext_retriever(
    query: str,
    retriever_config: RetrieverConfig,
    retriever_filter: Optional[RetrieverFilter] = None,
) -> list[DocumentPage]:
    """Retrieve pages via MongoDB Atlas Search $search.

    Uses the Atlas Search index for keyword-based retrieval.
    """
    search_index = retriever_config.search_index or "ft_pages"
    search_field = retriever_config.search_field or "content"

    # Build compound search query
    compound: dict = {
        "must": [{"text": {"query": query, "path": search_field}}]
    }

    # Pre-filter by document_ids
    if retriever_filter and retriever_filter.document_ids:
        compound["filter"] = [
            {"text": {"query": retriever_filter.document_ids, "path": "document_id"}}
        ]

    pipeline: list[dict] = [
        {"$search": {"index": search_index, "compound": compound}},
        {"$addFields": {"score": {"$meta": "searchScore"}}},
        {"$limit": retriever_config.top_k},
        {
            "$project": {
                "_id": 1,
                "document_id": 1,
                "page_number": 1,
                "content": 1,
                "content_markdown": 1,
                "content_html": 1,
                "height": 1,
                "width": 1,
                "unit": 1,
                "score": 1,
            }
        },
    ]

    log.debug(f"Fulltext retriever pipeline: {pipeline}")
    raw = await DocumentPage.aaggregate(pipeline)

    pages = []
    for doc in raw:
        page = DocumentPage(
            document_id=str(doc.get("document_id", "")),
            page_number=doc.get("page_number", 0),
            content=doc.get("content"),
            content_markdown=doc.get("content_markdown"),
            content_html=doc.get("content_html"),
            height=doc.get("height"),
            width=doc.get("width"),
            unit=doc.get("unit"),
        )
        page.id = str(doc["_id"])
        pages.append(page)

    log.info(f"Fulltext retriever returned {len(pages)} pages")
    return pages


async def get_pages_retriever(
    query: str,
    retriever_config: RetrieverConfig,
    retriever_filter: Optional[RetrieverFilter] = None,
) -> list[DocumentPage]:
    """Retrieve specific pages by ID.

    Used when page numbers are already known (e.g., from split/classify).
    The query parameter is ignored.
    """
    if not retriever_filter or not retriever_filter.page_ids:
        log.warning("pages_retriever called without page_ids, returning empty")
        return []

    pages = await DocumentPage.afind({"_id": {"$in": retriever_filter.page_ids}})
    log.info(f"Pages retriever returned {len(pages)} pages")
    return pages


# Register retrievers in the global registry
RETRIEVERS["vector_retriever"] = get_vector_retriever
RETRIEVERS["fulltext_retriever"] = get_fulltext_retriever
RETRIEVERS["pages_retriever"] = get_pages_retriever
