"""Reference resolution and result enrichment.

Resolves LLM reference strings (e.g., "d1:3:p5") to polygon coordinates
and builds enriched FieldResult objects from raw LLM output.
"""

import re
import typing
from datetime import datetime, timezone
from typing import Any, Optional, get_args, get_origin

from tinystructlog import get_logger

from mydocs.extracting.models import (
    FieldResult,
    LLMFieldItem,
    PageReference,
    Reference,
    ReferenceGranularity,
)
from mydocs.models import Document, DocumentPage

log = get_logger(__name__)


def get_inner_type(annotation: Any) -> Any:
    """Unwrap Optional[X] to X."""
    origin = get_origin(annotation)
    if origin is typing.Union:
        args = get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return annotation


# ---------------------------------------------------------------------------
# Polygon Calculation
# ---------------------------------------------------------------------------

def calculate_union_polygon(polygons: list[list[float]]) -> list[float]:
    """Compute bounding box union of multiple polygons.

    Each polygon is a flat list of [x1, y1, x2, y2, ...] coordinates.
    Returns [min_x, min_y, max_x, min_y, max_x, max_y, min_x, max_y]
    (a rectangular bounding box).
    """
    if not polygons:
        return []

    all_x = []
    all_y = []
    for poly in polygons:
        for i in range(0, len(poly), 2):
            if i + 1 < len(poly):
                all_x.append(poly[i])
                all_y.append(poly[i + 1])

    if not all_x:
        return []

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    return [min_x, min_y, max_x, min_y, max_x, max_y, min_x, max_y]


# ---------------------------------------------------------------------------
# Document Element Fetching
# ---------------------------------------------------------------------------

async def fetch_document_elements(
    document_ids: list[str],
) -> dict[str, Document]:
    """Fetch documents with their elements for reference resolution.

    Returns a dict mapping document_id to Document.
    """
    docs = await Document.afind({"_id": {"$in": document_ids}})
    return {str(doc.id): doc for doc in docs}


async def fetch_page_info(
    document_id: str,
    page_number: int,
) -> Optional[DocumentPage]:
    """Fetch a single page's metadata (dimensions)."""
    pages = await DocumentPage.afind({
        "document_id": document_id,
        "page_number": page_number,
    })
    return pages[0] if pages else None


# ---------------------------------------------------------------------------
# Reference Resolution
# ---------------------------------------------------------------------------

_REF_PATTERN = re.compile(
    r"d(\d+):(\d+):([a-z]+\d+)(?::(\d+))?"
)


def parse_reference_string(ref_str: str) -> Optional[dict]:
    """Parse a reference string like 'd1:3:p5' or 'd1:3:t3:2'.

    Returns dict with keys: doc_short_id, page_number, element_short_id,
    and optionally row_number.
    """
    match = _REF_PATTERN.match(ref_str.strip())
    if not match:
        log.warning(f"Could not parse reference string: {ref_str}")
        return None

    return {
        "doc_short_id": match.group(1),
        "page_number": int(match.group(2)),
        "element_short_id": match.group(3),
        "row_number": int(match.group(4)) if match.group(4) else None,
    }


def _find_element_by_short_id(doc: Document, short_id: str, page_number: int) -> Optional[dict]:
    """Find a DocumentElement in a document by short_id and page_number."""
    if not doc.elements:
        return None
    for elem in doc.elements:
        if elem.short_id == short_id and elem.page_number == page_number:
            return elem
    return None


def _get_element_polygon(element, row_number: Optional[int] = None) -> list[float]:
    """Extract polygon from element_data.

    For tables with row_number, computes union of that row's cell polygons.
    For key-value pairs, computes union of key and value bounding regions.
    """
    element_data = element.element_data if hasattr(element, "element_data") else element

    bounding_regions = element_data.get("boundingRegions", [])

    if row_number is not None:
        # Table row — compute union of cell polygons for the specified row
        cells = element_data.get("cells", [])
        row_polygons = []
        for cell in cells:
            if cell.get("rowIndex") == row_number:
                cell_regions = cell.get("boundingRegions", [])
                for region in cell_regions:
                    poly = region.get("polygon", [])
                    if poly:
                        row_polygons.append(poly)
        if row_polygons:
            return calculate_union_polygon(row_polygons)

    # Standard element — use bounding regions directly
    if bounding_regions:
        polygons = [r.get("polygon", []) for r in bounding_regions if r.get("polygon")]
        if polygons:
            return calculate_union_polygon(polygons)

    # Key-value pair — union of key and value regions
    key_regions = element_data.get("key", {}).get("boundingRegions", [])
    value_regions = element_data.get("value", {}).get("boundingRegions", [])
    all_regions = key_regions + value_regions
    if all_regions:
        polygons = [r.get("polygon", []) for r in all_regions if r.get("polygon")]
        if polygons:
            return calculate_union_polygon(polygons)

    return []


async def resolve_reference(
    ref_str: str,
    doc_short_to_long: dict[str, str],
    documents: dict[str, Document],
) -> Optional[Reference]:
    """Resolve a single LLM reference string to a Reference with polygon data.

    Args:
        ref_str: Reference string like "d1:3:p5" or "d1:3:t3:2"
        doc_short_to_long: Mapping of short doc IDs ("1") to actual document IDs
        documents: Pre-fetched Document objects keyed by document_id
    """
    parsed = parse_reference_string(ref_str)
    if not parsed:
        return None

    doc_id = doc_short_to_long.get(parsed["doc_short_id"])
    if not doc_id:
        log.warning(f"Unknown document short ID: d{parsed['doc_short_id']}")
        return None

    doc = documents.get(doc_id)
    if not doc:
        log.warning(f"Document not found: {doc_id}")
        return None

    element = _find_element_by_short_id(doc, parsed["element_short_id"], parsed["page_number"])
    if not element:
        log.warning(
            f"Element {parsed['element_short_id']} not found on page "
            f"{parsed['page_number']} of document {doc_id}"
        )
        return None

    polygon = _get_element_polygon(element, parsed.get("row_number"))

    # Get page info for dimensions
    page = await fetch_page_info(doc_id, parsed["page_number"])
    page_id = str(page.id) if page else ""
    page_width = page.width if page and page.width else 0.0
    page_height = page.height if page and page.height else 0.0
    page_unit = page.unit if page and page.unit else "inch"

    return Reference(
        document_id=doc_id,
        page_id=page_id,
        page_number=parsed["page_number"],
        page_width=page_width,
        page_height=page_height,
        page_unit=page_unit,
        element_type=element.type if hasattr(element, "type") else "unknown",
        element_short_id=parsed["element_short_id"],
        polygon=polygon,
        llm_reference=ref_str,
    )


async def resolve_page_reference(
    ref_str: str,
    doc_short_to_long: dict[str, str],
) -> Optional[PageReference]:
    """Resolve a reference string to a PageReference (page granularity only)."""
    parsed = parse_reference_string(ref_str)
    if not parsed:
        return None

    doc_id = doc_short_to_long.get(parsed["doc_short_id"])
    if not doc_id:
        return None

    page = await fetch_page_info(doc_id, parsed["page_number"])
    if not page:
        return None

    return PageReference(
        document_id=doc_id,
        page_id=str(page.id),
        page_number=parsed["page_number"],
    )


# ---------------------------------------------------------------------------
# LLM Result → FieldResult Conversion
# ---------------------------------------------------------------------------

def llm_field_to_result(
    item: LLMFieldItem,
    model_name: str,
    references: Optional[list[Reference]] = None,
    page_references: Optional[list[PageReference]] = None,
) -> FieldResult:
    """Convert an LLMFieldItem to a FieldResult."""
    return FieldResult(
        content=item.content if item.content else None,
        justification=item.justification if item.justification else None,
        citation=item.citation if item.citation else None,
        references=references,
        page_references=page_references,
        created_by=model_name,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Batch Enrichment
# ---------------------------------------------------------------------------

def _detect_composite_items(llm_result) -> bool:
    """Check if llm_result.result items have LLMFieldItem sub-fields."""
    if not hasattr(llm_result, "result") or not isinstance(llm_result.result, list):
        return False
    if not llm_result.result:
        return False
    item = llm_result.result[0]
    if not hasattr(item, "model_fields"):
        return False
    for field_info in item.model_fields.values():
        inner = get_inner_type(field_info.annotation) if field_info.annotation else None
        if inner is LLMFieldItem:
            return True
    return False


def _extract_parent_name(fields: list) -> str:
    """Extract composite parent name from dot-notation field names.

    E.g., fields with names like 'line_items.item_description' → 'line_items'.
    """
    for field in fields:
        name = field.name if hasattr(field, "name") else str(field)
        if "." in name:
            return name.split(".")[0]
    return "items"


async def enrich_composite_field_results(
    items: list,
    doc_short_to_long: dict[str, str],
    reference_granularity: ReferenceGranularity,
    model_name: str,
    parent_field_name: str,
) -> dict[str, list[dict[str, FieldResult]]]:
    """Enrich composite schema items that have LLMFieldItem sub-fields.

    For each item in the list, iterates its fields. For each LLMFieldItem
    sub-field, resolves references using the same helpers as flat enrichment.

    Returns {parent_field_name: [item_dict_0, item_dict_1, ...]}
    where each item_dict maps sub-field names to FieldResult.
    """
    if reference_granularity == ReferenceGranularity.NONE:
        result_items = []
        for item in items:
            item_dict: dict[str, FieldResult] = {}
            for field_name in item.model_fields:
                value = getattr(item, field_name, None)
                if isinstance(value, LLMFieldItem):
                    item_dict[field_name] = llm_field_to_result(value, model_name)
            result_items.append(item_dict)
        return {parent_field_name: result_items}

    # Pre-fetch documents for reference resolution
    all_doc_ids = list(set(doc_short_to_long.values()))
    documents = await fetch_document_elements(all_doc_ids) if all_doc_ids else {}

    result_items = []
    for item in items:
        item_dict: dict[str, FieldResult] = {}
        for field_name in item.model_fields:
            value = getattr(item, field_name, None)
            if not isinstance(value, LLMFieldItem):
                continue

            resolved_refs: Optional[list[Reference]] = None
            resolved_page_refs: Optional[list[PageReference]] = None

            if value.references:
                if reference_granularity == ReferenceGranularity.FULL:
                    resolved_refs = []
                    for ref_str in value.references:
                        ref = await resolve_reference(ref_str, doc_short_to_long, documents)
                        if ref:
                            resolved_refs.append(ref)

                elif reference_granularity == ReferenceGranularity.PAGE:
                    resolved_page_refs = []
                    seen_pages: set[tuple[str, int]] = set()
                    for ref_str in value.references:
                        page_ref = await resolve_page_reference(ref_str, doc_short_to_long)
                        if page_ref:
                            key = (page_ref.document_id, page_ref.page_number)
                            if key not in seen_pages:
                                seen_pages.add(key)
                                resolved_page_refs.append(page_ref)

            item_dict[field_name] = llm_field_to_result(
                value, model_name, resolved_refs, resolved_page_refs
            )
        result_items.append(item_dict)

    return {parent_field_name: result_items}


async def enrich_field_results(
    llm_result: list[LLMFieldItem],
    doc_short_to_long: dict[str, str],
    reference_granularity: ReferenceGranularity,
    model_name: str,
) -> dict[str, FieldResult]:
    """Enrich a list of LLMFieldItem objects into FieldResult objects.

    Behavior depends on reference_granularity:
    - full: Resolve polygon coordinates from document elements
    - page: Build PageReference objects (no polygons)
    - none: Content value only
    """
    results: dict[str, FieldResult] = {}

    if reference_granularity == ReferenceGranularity.NONE:
        for item in llm_result:
            results[item.name] = llm_field_to_result(item, model_name)
        return results

    # Pre-fetch documents for reference resolution (full and page modes)
    all_doc_ids = list(set(doc_short_to_long.values()))
    documents = await fetch_document_elements(all_doc_ids) if all_doc_ids else {}

    for item in llm_result:
        resolved_refs: Optional[list[Reference]] = None
        resolved_page_refs: Optional[list[PageReference]] = None

        if item.references:
            if reference_granularity == ReferenceGranularity.FULL:
                resolved_refs = []
                for ref_str in item.references:
                    ref = await resolve_reference(ref_str, doc_short_to_long, documents)
                    if ref:
                        resolved_refs.append(ref)

            elif reference_granularity == ReferenceGranularity.PAGE:
                resolved_page_refs = []
                seen_pages: set[tuple[str, int]] = set()
                for ref_str in item.references:
                    page_ref = await resolve_page_reference(ref_str, doc_short_to_long)
                    if page_ref:
                        key = (page_ref.document_id, page_ref.page_number)
                        if key not in seen_pages:
                            seen_pages.add(key)
                            resolved_page_refs.append(page_ref)

        results[item.name] = llm_field_to_result(
            item, model_name, resolved_refs, resolved_page_refs
        )

    return results
