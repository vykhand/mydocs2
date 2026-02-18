"""Data models for the extracting engine.

Includes enums, field definitions, extraction results, LLM I/O models,
request/response models, MongoDB records, config models, and pipeline state.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Optional

from lightodm import MongoBaseModel
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ReferenceGranularity(StrEnum):
    FULL = "full"
    PAGE = "page"
    NONE = "none"


class ContentMode(StrEnum):
    MARKDOWN = "markdown"
    HTML = "html"


class ExtractionMode(StrEnum):
    REFERENCED = "referenced"
    DIRECT = "direct"


class FieldDataType(StrEnum):
    STRING = "string"
    DATE = "date"
    NUMBER = "number"
    CURRENCY = "currency"
    BOOLEAN = "boolean"
    ENUM = "enum"
    TEXT = "text"


# ---------------------------------------------------------------------------
# Field Definitions
# ---------------------------------------------------------------------------

class FieldValueOption(BaseModel):
    name: str
    prompt: Optional[str] = None


class FieldRequirement(BaseModel):
    field_name: str
    document_type: Optional[str] = None


class FieldDefinition(BaseModel):
    name: str
    description: str
    data_type: FieldDataType = FieldDataType.STRING
    prompt: Optional[str] = None
    value_list: Optional[list[FieldValueOption]] = None
    group: int = 0
    inputs: Optional[list[FieldRequirement]] = None


# ---------------------------------------------------------------------------
# References and Results
# ---------------------------------------------------------------------------

class Reference(BaseModel):
    """Source location in the original document (full granularity)."""
    document_id: str
    page_id: str
    page_number: int
    page_width: float
    page_height: float
    page_unit: str
    element_type: str
    element_short_id: str
    polygon: list[float]
    llm_reference: Optional[str] = None


class PageReference(BaseModel):
    """Lightweight page-level reference (page granularity)."""
    document_id: str
    page_id: str
    page_number: int


class FieldResult(BaseModel):
    """Result of extracting a single field."""
    content: Optional[str] = None
    justification: Optional[str] = None
    citation: Optional[str] = None
    references: Optional[list[Reference]] = None
    page_references: Optional[list[PageReference]] = None
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


class FieldReference(BaseModel):
    """Reference annotation for a single leaf field in direct mode."""
    field_path: str
    citation: Optional[str] = None
    justification: Optional[str] = None
    references: Optional[list[Reference]] = None
    page_references: Optional[list[PageReference]] = None


class ReferenceInferenceResult(BaseModel):
    """Output of the reference-inference pass."""
    field_references: list[FieldReference]


# ---------------------------------------------------------------------------
# LLM Input/Output Models
# ---------------------------------------------------------------------------

class LLMFieldItem(BaseModel):
    """Single extracted field from the LLM."""
    name: str
    content: str
    justification: str
    citation: str
    references: list[str]


class LLMFieldsResult(BaseModel):
    """Container for LLM field extraction output."""
    result: list[LLMFieldItem]


# ---------------------------------------------------------------------------
# Split / Classify Models
# ---------------------------------------------------------------------------

class SplitSegment(BaseModel):
    """A classified segment within a multi-document file."""
    document_type: str
    page_numbers: list[int]


class SplitClassifyResult(BaseModel):
    """Result of splitting and classifying a document."""
    segments: list[SplitSegment]
    subdocuments: list[Any] = Field(default_factory=list)  # list[SubDocument] from models.py


class LLMSplitClassifyBatchResult(BaseModel):
    """LLM output for a batch of pages."""
    result: list[SplitSegment]


# ---------------------------------------------------------------------------
# Case Type Configuration
# ---------------------------------------------------------------------------

class DocumentTypeConfig(BaseModel):
    """Configuration for a document type within a case type."""
    name: str
    description: Optional[str] = None
    target_object: Optional[str] = None

class SplitClassifyConfig(BaseModel):
    """Split/classify enablement for a case type."""
    enabled: bool = False
    prompt_name: str = "main"

class CaseTypeConfig(BaseModel):
    """Top-level configuration for a case type."""
    name: str
    description: Optional[str] = None
    split_classify: SplitClassifyConfig = Field(default_factory=SplitClassifyConfig)
    document_types: list[DocumentTypeConfig] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Request / Response (HTTP API)
# ---------------------------------------------------------------------------

class ExtractionRequest(BaseModel):
    """Request to extract fields from documents."""
    case_id: Optional[str] = None
    case_type: str = "generic"
    document_type: str
    extraction_mode: ExtractionMode = ExtractionMode.REFERENCED
    output_schema: Optional[str] = None
    infer_references: bool = False

    document_ids: Optional[list[str]] = None
    page_ids: Optional[list[str]] = None
    file_ids: Optional[list[str]] = None

    fields: Optional[list[str]] = None
    field_overrides: Optional[list[FieldDefinition]] = None

    reference_granularity: ReferenceGranularity = ReferenceGranularity.FULL
    content_mode: ContentMode = ContentMode.MARKDOWN

    subdocument_id: Optional[str] = None


class ExtractionResponse(BaseModel):
    """Response from field extraction."""
    document_id: str
    document_type: str
    case_type: str
    extraction_mode: str
    results: dict
    reference_annotations: Optional[list[FieldReference]] = None
    subdocument_id: Optional[str] = None
    target_object_id: Optional[str] = None
    model_used: str
    reference_granularity: str


# ---------------------------------------------------------------------------
# MongoDB Records
# ---------------------------------------------------------------------------

class FieldResultRecord(MongoBaseModel):
    document_id: str
    document_type: str
    subdocument_id: str = ""
    case_type: str = "generic"
    field_name: str
    result: FieldResult

    class Settings:
        name = "field_results"
        composite_key = ["document_id", "subdocument_id", "field_name"]


class UserFieldDefinition(MongoBaseModel):
    case_type: str = "generic"
    document_type: str
    field: FieldDefinition
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None

    class Settings:
        name = "user_field_definitions"
        composite_key = ["case_type", "document_type", "field.name"]


# ---------------------------------------------------------------------------
# Config Models
# ---------------------------------------------------------------------------

class RetrieverConfig(BaseModel):
    """Configuration for context retrieval."""
    name: str
    retriever_kwargs: dict = Field(default_factory=dict)

    # Vector retriever settings
    index_name: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_field: Optional[str] = None
    content_field: str = "content_markdown"
    top_k: int = 10
    relevance_score_fn: Optional[str] = None
    search_type: Optional[str] = None

    # Fulltext retriever settings
    search_index: Optional[str] = None
    search_field: Optional[str] = None


class PromptConfig(BaseModel):
    """LLM prompt configuration for field extraction."""
    name: str
    case_type: str = "generic"
    document_type: Optional[str] = None
    groups: Optional[list[int]] = None
    output_schema: str = "default"

    sys_prompt_template: str
    user_prompt_template: str
    model: str = "gpt-4.1"
    validation_retries: int = 3
    transport_retries: int = 3
    llm_kwargs: dict = Field(default_factory=dict)

    retriever_config: Optional[RetrieverConfig] = None
    content_mode: ContentMode = ContentMode.MARKDOWN
    reference_granularity: ReferenceGranularity = ReferenceGranularity.FULL

    # Split/classify specific
    batch_size: Optional[int] = None
    overlap_factor: Optional[int] = None

    # Versioning
    hash: Optional[str] = None
    version: Optional[int] = None


# ---------------------------------------------------------------------------
# Pipeline State Models
# ---------------------------------------------------------------------------

class FieldPrompt(BaseModel):
    """Field definition formatted for prompt insertion."""
    name: str
    description: str
    prompt: Optional[str] = None
    value_list: Optional[list[FieldValueOption]] = None


class FieldInput(BaseModel):
    """Previously extracted field value used as input for dependent fields."""
    field_name: str
    document_type: Optional[str] = None
    content: Optional[str] = None


class PromptInput(BaseModel):
    """Complete input for a single LLM extraction call."""
    field_prompts: list[FieldPrompt]
    field_inputs: Optional[list[FieldInput]] = None


class RetrieverFilter(BaseModel):
    """Filter for scoping retrieval to specific documents/pages."""
    document_ids: Optional[list[str]] = None
    page_ids: Optional[list[str]] = None


class SubgraphOutput(BaseModel):
    """Output from a single group subgraph execution."""
    field_results: dict[str, FieldResult] = Field(default_factory=dict)


class ExtractGroupState(BaseModel):
    """State for a single extraction group subgraph."""
    group_id: int = 0
    fields: list[FieldDefinition] = Field(default_factory=list)
    prompt_config: Optional[PromptConfig] = None
    prompt_input: Optional[PromptInput] = None
    retriever_filter: Optional[RetrieverFilter] = None
    retrieved_pages: list[Any] = Field(default_factory=list)
    context: Optional[str] = None
    doc_short_to_long: dict[str, str] = Field(default_factory=dict)
    llm_result: Optional[Any] = None
    field_results: dict[str, FieldResult] = Field(default_factory=dict)
    extraction_mode: ExtractionMode = ExtractionMode.REFERENCED
    content_mode: ContentMode = ContentMode.MARKDOWN
    reference_granularity: ReferenceGranularity = ReferenceGranularity.FULL
    output_schema_name: str = "default"


class ExtractorState(BaseModel):
    """Top-level state for the extraction pipeline."""
    # Request info
    case_id: Optional[str] = None
    case_type: str = "generic"
    document_type: str = "generic"
    document_ids: list[str] = Field(default_factory=list)
    page_ids: Optional[list[str]] = None
    subdocument_id: str = ""
    extraction_mode: ExtractionMode = ExtractionMode.REFERENCED
    output_schema_name: str = "default"
    infer_references: bool = False
    reference_granularity: ReferenceGranularity = ReferenceGranularity.FULL
    content_mode: ContentMode = ContentMode.MARKDOWN

    # Field definitions
    field_definitions: list[FieldDefinition] = Field(default_factory=list)
    field_groups: dict[int, list[FieldDefinition]] = Field(default_factory=dict)

    # Prompt configs
    prompt_configs: dict[int, PromptConfig] = Field(default_factory=dict)

    # Retriever
    retriever_filter: Optional[RetrieverFilter] = None

    # Results
    field_results: dict[str, FieldResult] = Field(default_factory=dict)
    group_outputs: list[SubgraphOutput] = Field(default_factory=list)

    # Response metadata
    model_used: Optional[str] = None
