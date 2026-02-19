"""Target object models for the generic case type."""

from typing import Optional

from lightodm import MongoBaseModel
from pydantic import BaseModel

from mydocs.extracting.models import FieldResult


class ReceiptLineItem(BaseModel):
    """A single line item on a receipt."""
    item_description: Optional[FieldResult] = None
    quantity: Optional[FieldResult] = None
    unit_price: Optional[FieldResult] = None
    line_total: Optional[FieldResult] = None


class Receipt(MongoBaseModel):
    """Target object for receipt extraction results."""
    document_id: str
    subdocument_id: str = ""
    case_id: str = ""

    summary: Optional[FieldResult] = None
    merchant_name: Optional[FieldResult] = None
    merchant_address: Optional[FieldResult] = None
    receipt_number: Optional[FieldResult] = None
    transaction_date: Optional[FieldResult] = None
    payment_method: Optional[FieldResult] = None
    country: Optional[FieldResult] = None
    subtotal: Optional[FieldResult] = None
    tax_total: Optional[FieldResult] = None
    total_amount: Optional[FieldResult] = None
    currency: Optional[FieldResult] = None
    line_items: Optional[list[ReceiptLineItem]] = None

    class Settings:
        name = "receipts"
        composite_key = ["document_id", "subdocument_id"]
