"""Target object population and type coercion.

Handles coercing FieldResult values to target object field types
and populating target objects from extraction results.
"""

import typing
from typing import Any, Optional, get_args, get_origin

from tinystructlog import get_logger

from mydocs.extracting.models import FieldResult

log = get_logger(__name__)


def get_inner_type(annotation: Any) -> Any:
    """Unwrap Optional[X] to X.

    If the annotation is Optional[X] (i.e., Union[X, None]), returns X.
    Otherwise returns the annotation as-is.
    """
    origin = get_origin(annotation)
    if origin is typing.Union:
        args = get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return annotation


def coerce_field_result(field_result: FieldResult, target_type: Any) -> Any:
    """Coerce a FieldResult to the target type.

    - FieldResult → FieldResult: pass-through
    - FieldResult → str: return .content
    - FieldResult → int: int(.content)
    - FieldResult → float: float(.content)
    - FieldResult → bool: bool evaluation of .content
    """
    inner = get_inner_type(target_type)

    if inner is FieldResult:
        return field_result

    value = field_result.content
    if value is None:
        return None

    try:
        if inner is str:
            return value
        if inner is int:
            return int(value)
        if inner is float:
            return float(value)
        if inner is bool:
            return value.lower() not in ("false", "0", "no", "n", "")
    except (ValueError, TypeError) as e:
        log.warning(f"Could not coerce '{value}' to {inner}: {e}")
        return None

    # Unsupported target type — return content as-is
    return value


def _get_list_item_type(annotation: Any) -> Any:
    """Unwrap Optional[list[X]] to X.

    Returns X if annotation matches Optional[list[X]], else None.
    """
    inner = get_inner_type(annotation)
    origin = get_origin(inner)
    if origin is list:
        args = get_args(inner)
        if args:
            return args[0]
    return None


def populate_target_object(
    target_obj: Any,
    field_results: dict[str, FieldResult],
    composite_results: dict[str, list[dict[str, FieldResult]]] | None = None,
) -> None:
    """Populate a target object's fields from extraction results.

    Iterates over the target model's fields (excluding internal fields like
    id, document_id, subdocument_id, case_id), matches them by name against
    field_results, and coerces values to the declared field type.

    For composite results (e.g., line items), converts each item dict to
    the appropriate model type and sets the list on the target object.
    """
    skip_fields = {"id", "document_id", "subdocument_id", "case_id"}
    model_fields = target_obj.model_fields

    for field_name, field_info in model_fields.items():
        if field_name in skip_fields:
            continue

        if field_name not in field_results:
            continue

        field_result = field_results[field_name]
        target_type = field_info.annotation
        coerced = coerce_field_result(field_result, target_type)

        if coerced is not None:
            setattr(target_obj, field_name, coerced)

    if not composite_results:
        return

    for field_name, items in composite_results.items():
        if field_name in skip_fields or field_name not in model_fields:
            continue
        item_type = _get_list_item_type(model_fields[field_name].annotation)
        if item_type:
            instances = [item_type(**item) for item in items]
            setattr(target_obj, field_name, instances)
