"""Search endpoint handlers."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from mydocs.parsing.config import EmbeddingConfig, ParserConfig
from mydocs.retrieval.models import SearchRequest, SearchResponse
from mydocs.retrieval.search import VECTOR_INDEX_MAP
from mydocs.retrieval.search import search as retrieval_search

router = APIRouter(prefix="/api/v1/search")


def _error(status_code: int, error_code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "error_code": error_code, "status_code": status_code},
    )


def _similarity_from_index_name(index_name: str) -> str:
    if index_name.endswith("_cos"):
        return "cosine"
    return "dotProduct"


def _build_index_info(emb: EmbeddingConfig, search_target: str) -> dict | None:
    key = (search_target, emb.target_field)
    index_name = VECTOR_INDEX_MAP.get(key)
    if index_name is None:
        return None
    return {
        "index_name": index_name,
        "embedding_model": emb.model,
        "field": emb.target_field,
        "dimensions": emb.dimensions,
        "similarity": _similarity_from_index_name(index_name),
    }


@router.post("/", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    try:
        return await retrieval_search(request)
    except ValueError as exc:
        return _error(400, "INVALID_REQUEST", str(exc))


@router.get("/indices")
async def list_indices():
    config = ParserConfig()

    pages = []
    for emb in config.page_embeddings or []:
        info = _build_index_info(emb, "pages")
        if info:
            pages.append(info)

    documents = []
    for emb in config.document_embeddings or []:
        info = _build_index_info(emb, "documents")
        if info:
            documents.append(info)

    return {"pages": pages, "documents": documents}
