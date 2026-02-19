"""Schema, retriever, and target object registries for the extracting engine."""

from typing import Callable, Optional

from lightodm import MongoBaseModel
from pydantic import BaseModel

from mydocs.extracting.exceptions import RetrieverNotFoundError, SchemaNotFoundError
from mydocs.extracting.models import LLMFieldsResult, LLMSplitClassifyBatchResult
from mydocs.extracting.schemas.receipt import LLMReceiptLineItemsResult

# Schema registry: maps schema names to Pydantic output models
SCHEMAS: dict[str, type[BaseModel]] = {
    "default": LLMFieldsResult,
    "split_classify": LLMSplitClassifyBatchResult,
    "receipt_line_items": LLMReceiptLineItemsResult,
}

# Retriever registry: maps retriever names to async functions
# Populated by retrievers.py on import to avoid circular imports
RETRIEVERS: dict[str, Callable] = {}

# Target object registry: maps (case_type, document_type) to MongoBaseModel subclasses
TARGET_OBJECTS: dict[tuple[str, str], type[MongoBaseModel]] = {}


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


def register_target_object(
    case_type: str,
    document_type: str,
    model_class: type[MongoBaseModel],
) -> None:
    """Register a target object class for a (case_type, document_type) pair."""
    TARGET_OBJECTS[(case_type, document_type)] = model_class


def get_target_object_class(
    case_type: str,
    document_type: str,
) -> Optional[type[MongoBaseModel]]:
    """Look up the registered target object class."""
    return TARGET_OBJECTS.get((case_type, document_type))
