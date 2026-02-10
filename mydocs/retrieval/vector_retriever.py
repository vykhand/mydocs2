"""Vector search via MongoDB Atlas $vectorSearch stage."""

from tinystructlog import get_logger

from mydocs.parsing.models import Document, DocumentPage
from mydocs.retrieval.models import SearchFilters

log = get_logger(__name__)


async def vector_search(
    query_embedding: list[float],
    search_target: str,
    index_name: str,
    vector_field: str,
    filters: SearchFilters,
    num_candidates: int,
    top_k: int,
) -> list[dict]:
    """Execute Atlas $vectorSearch and return normalized result dicts."""
    if search_target == "documents":
        return await _search_documents(
            query_embedding, index_name, vector_field, filters, num_candidates, top_k,
        )
    else:
        return await _search_pages(
            query_embedding, index_name, vector_field, filters, num_candidates, top_k,
        )


async def _search_documents(
    query_embedding: list[float],
    index_name: str,
    vector_field: str,
    filters: SearchFilters,
    num_candidates: int,
    top_k: int,
) -> list[dict]:
    """Vector search on the documents collection."""
    vector_stage: dict = {
        "$vectorSearch": {
            "index": index_name,
            "path": vector_field,
            "queryVector": query_embedding,
            "numCandidates": num_candidates,
            "limit": top_k,
        }
    }

    pipeline: list[dict] = [
        vector_stage,
        {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
    ]

    # Post-search $match for all document-level filters
    post_match: dict = {}
    if filters.tags:
        post_match["tags"] = {"$all": filters.tags}
    if filters.file_type:
        post_match["file_type"] = filters.file_type
    if filters.document_ids:
        post_match["_id"] = {"$in": filters.document_ids}
    if filters.status:
        post_match["status"] = filters.status
    if filters.document_type:
        post_match["document_type"] = filters.document_type
    if post_match:
        pipeline.append({"$match": post_match})

    pipeline.append({
        "$project": {
            "_id": 1, "score": 1, "content": 1, "content_markdown": 1,
            "file_name": 1, "tags": 1,
        }
    })

    log.debug(f"vector documents pipeline: {pipeline}")
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
    query_embedding: list[float],
    index_name: str,
    vector_field: str,
    filters: SearchFilters,
    num_candidates: int,
    top_k: int,
) -> list[dict]:
    """Vector search on the pages collection with pre-filter on document_id."""
    vector_stage: dict = {
        "$vectorSearch": {
            "index": index_name,
            "path": vector_field,
            "queryVector": query_embedding,
            "numCandidates": num_candidates,
            "limit": top_k,
        }
    }

    # Pre-filter on document_id (supported by the vector index filter field)
    if filters.document_ids:
        vector_stage["$vectorSearch"]["filter"] = {
            "document_id": {"$in": filters.document_ids}
        }

    pipeline: list[dict] = [
        vector_stage,
        {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
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

    log.debug(f"vector pages pipeline: {pipeline}")
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
