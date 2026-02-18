"""LLM-based field extraction from parsed documents."""

# Import retrievers to populate the registry on package import
import mydocs.extracting.retrievers  # noqa: F401

# Import case_types to trigger target object registration
import mydocs.extracting.case_types  # noqa: F401
