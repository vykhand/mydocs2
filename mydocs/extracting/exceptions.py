"""Extracting engine exceptions."""


class ExtractionError(Exception):
    """Base exception for extraction errors."""


class NoDocumentsFoundError(ExtractionError):
    """Raised when no documents are found for the extraction request."""


class FieldConsistencyError(ExtractionError):
    """Raised when field definitions are inconsistent with prompt configuration."""


class ConfigNotFoundError(ExtractionError):
    """Raised when required configuration files are not found."""


class SchemaNotFoundError(ExtractionError):
    """Raised when a requested output schema is not registered."""


class RetrieverNotFoundError(ExtractionError):
    """Raised when a requested retriever is not registered."""
