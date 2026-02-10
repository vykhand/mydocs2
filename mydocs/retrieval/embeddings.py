"""Query embedding generation via litellm."""

import litellm
from tinystructlog import get_logger

log = get_logger(__name__)


async def generate_query_embedding(query: str, model: str) -> list[float]:
    """Generate an embedding vector for a search query."""
    log.debug("generating query embedding", model=model)
    response = await litellm.aembedding(
        model=model,
        input=[query],
    )
    return response.data[0]["embedding"]
