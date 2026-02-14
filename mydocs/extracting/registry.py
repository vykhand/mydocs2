"""Schema and retriever registries for the extracting engine."""

from typing import Callable

from pydantic import BaseModel

from mydocs.extracting.exceptions import RetrieverNotFoundError, SchemaNotFoundError
from mydocs.extracting.models import LLMFieldsResult, LLMSplitClassifyBatchResult

# Schema registry: maps schema names to Pydantic output models
SCHEMAS: dict[str, type[BaseModel]] = {
    "default": LLMFieldsResult,
    "split_classify": LLMSplitClassifyBatchResult,
}

# Retriever registry: maps retriever names to async functions
# Populated by retrievers.py on import to avoid circular imports
RETRIEVERS: dict[str, Callable] = {}


def get_schema(name: str) -> type[BaseModel]:
    """Look up a registered output schema by name."""
    if name not in SCHEMAS:
        raise SchemaNotFoundError(f"Schema '{name}' not registered. Available: {list(SCHEMAS.keys())}")
    return SCHEMAS[name]


def get_retriever(name: str) -> Callable:
    """Look up a registered retriever function by name."""
    if name not in RETRIEVERS:
        raise RetrieverNotFoundError(f"Retriever '{name}' not registered. Available: {list(RETRIEVERS.keys())}")
    return RETRIEVERS[name]
