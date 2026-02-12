"""Full-text search via MongoDB Atlas Search $search stage."""

from tinystructlog import get_logger

from mydocs.models import Document, DocumentPage
from mydocs.retrieval.models import FullTextSearchConfig, SearchFilters

log = get_logger(__name__)


def _build_text_operator(query: str, field: str, fuzzy: dict | None = None) -> dict:
    """Build Atlas Search text operator."""
    op = {"text": {"query": query, "path": field}}
    if fuzzy:
        op["text"]["fuzzy"] = fuzzy
    return op


def _build_fuzzy_opts(config: FullTextSearchConfig) -> dict | None:
    if not config.fuzzy.enabled:
        return None
    return {
        "maxEdits": config.fuzzy.max_edits,
        "prefixLength": config.fuzzy.prefix_length,
    }


async def fulltext_search(
    query: str,
    search_target: str,
    fulltext_config: FullTextSearchConfig,
    filters: SearchFilters,
    top_k: int,
) -> list[dict]:
    """Execute Atlas Search $search and return normalized result dicts."""
    if search_target == "documents":
        return await _search_documents(query, fulltext_config, filters, top_k)
    else:
        return await _search_pages(query, fulltext_config, filters, top_k)


async def _search_documents(
    query: str,
    config: FullTextSearchConfig,
    filters: SearchFilters,
    top_k: int,
) -> list[dict]:
    """Full-text search on the documents collection using ft_documents index."""
    fuzzy_opts = _build_fuzzy_opts(config)
    text_op = _build_text_operator(query, config.content_field, fuzzy_opts)

    # Build compound must/filter clauses for keyword-indexed fields
    compound: dict = {"must": [text_op]}
    filter_clauses = []
    if filters.tags:
        filter_clauses.append({"text": {"query": filters.tags, "path": "tags"}})
    if filters.status:
        filter_clauses.append({"text": {"query": filters.status, "path": "status"}})
    if filters.document_type:
        filter_clauses.append({"text": {"query": filters.document_type, "path": "document_type"}})
    if filter_clauses:
        compound["filter"] = filter_clauses

    pipeline: list[dict] = [
        {"$search": {"index": "ft_documents", "compound": compound}},
        {"$addFields": {"score": {"$meta": "searchScore"}}},
    ]

    # Post-search $match for fields not in the search index
    post_match: dict = {}
    if filters.file_type:
        post_match["file_type"] = filters.file_type
    if filters.document_ids:
        post_match["_id"] = {"$in": filters.document_ids}
    if post_match:
        pipeline.append({"$match": post_match})

    pipeline.append({"$limit": top_k})
    pipeline.append({
        "$project": {
            "_id": 1, "score": 1, "content": 1, "content_markdown": 1,
            "file_name": 1, "tags": 1,
        }
    })

    log.debug(f"fulltext documents pipeline: {pipeline}")
    raw = await Document.aaggregate(pipeline)

    results = []
    for doc in raw:
        results.append({
            "id": str(doc["_id"]),
            "document_id": str(doc["_id"]),
            "page_number": None,
            "score": doc.get("score", 0.0),
            "content": doc.get("content"),
            "content_markdown": doc.get("content_markdown"),
            "file_name": doc.get("file_name"),
            "tags": doc.get("tags", []),
        })
    return results


async def _search_pages(
    query: str,
    config: FullTextSearchConfig,
    filters: SearchFilters,
    top_k: int,
) -> list[dict]:
    """Full-text search on the pages collection using ft_pages index."""
    fuzzy_opts = _build_fuzzy_opts(config)
    text_op = _build_text_operator(query, config.content_field, fuzzy_opts)

    compound: dict = {"must": [text_op]}
    # ft_pages index has document_id as keyword field
    filter_clauses = []
    if filters.document_ids:
        filter_clauses.append({"text": {"query": filters.document_ids, "path": "document_id"}})
    if filter_clauses:
        compound["filter"] = filter_clauses

    pipeline: list[dict] = [
        {"$search": {"index": "ft_pages", "compound": compound}},
        {"$addFields": {"score": {"$meta": "searchScore"}}},
        {"$limit": top_k},
        # Lookup to documents for enrichment and doc-level filtering
        {
            "$lookup": {
                "from": "documents",
                "localField": "document_id",
                "foreignField": "_id",
                "as": "_doc",
            }
        },
        {"$unwind": {"path": "$_doc", "preserveNullAndEmptyArrays": True}},
    ]

    # Apply doc-level filters post-lookup
    doc_match: dict = {}
    if filters.tags:
        doc_match["_doc.tags"] = {"$all": filters.tags}
    if filters.file_type:
        doc_match["_doc.file_type"] = filters.file_type
    if filters.status:
        doc_match["_doc.status"] = filters.status
    if filters.document_type:
        doc_match["_doc.document_type"] = filters.document_type
    if doc_match:
        pipeline.append({"$match": doc_match})

    pipeline.append({
        "$project": {
            "_id": 1, "document_id": 1, "page_number": 1, "score": 1,
            "content": 1, "content_markdown": 1,
            "file_name": "$_doc.file_name", "tags": "$_doc.tags",
        }
    })

    log.debug(f"fulltext pages pipeline: {pipeline}")
    raw = await DocumentPage.aaggregate(pipeline)

    results = []
    for doc in raw:
        results.append({
            "id": str(doc["_id"]),
            "document_id": str(doc.get("document_id", "")),
            "page_number": doc.get("page_number"),
            "score": doc.get("score", 0.0),
            "content": doc.get("content"),
            "content_markdown": doc.get("content_markdown"),
            "file_name": doc.get("file_name"),
            "tags": doc.get("tags", []),
        })
    return results
