"""Query embedding generation via litellm."""

import litellm
from tinystructlog import get_logger

import mydocs.config as C

log = get_logger(__name__)


async def generate_query_embedding(query: str, model: str) -> list[float]:
    """Generate an embedding vector for a search query."""
    log.debug("generating query embedding", model=model)
    response = await litellm.aembedding(
        model=model,
        input=[query],
        api_key=C.LLM_API_KEY,
        api_base=C.LLM_API_BASE,
    )
    return response.data[0]["embedding"]
