"""Generic case type — registers target objects for generic document types."""

from mydocs.extracting.case_types.generic.models import Receipt  # noqa: F401
from mydocs.extracting.registry import register_target_object

register_target_object("generic", "receipt", Receipt)
