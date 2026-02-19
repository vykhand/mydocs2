"""Receipt line item extraction schema."""

from pydantic import BaseModel

from mydocs.extracting.models import LLMFieldItem


class LLMReceiptLineItem(BaseModel):
    """Single receipt line item with LLMFieldItem sub-fields for reference tracking."""
    item_description: LLMFieldItem
    quantity: LLMFieldItem
    unit_price: LLMFieldItem
    line_total: LLMFieldItem


class LLMReceiptLineItemsResult(BaseModel):
    """Container for receipt line item extraction output."""
    result: list[LLMReceiptLineItem]
