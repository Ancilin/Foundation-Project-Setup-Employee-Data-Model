"""Pydantic schemas for Clients, Invoices, Invoice Items, Payments, and Receivables (LF-10)."""

from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: str
    client_name: str
    industry: str
    city: str
    state_or_region: str
    country: str
    client_type: str
    gst_registration: str | None = None
    payment_terms_days: int
    payment_behaviour: str | None = None
    primary_service_line: int
    contact_email: str
    onboarded_on: date
    is_active: str


class InvoiceItemInput(BaseModel):
    description: str = Field(..., min_length=1, max_length=255)
    quantity: Decimal = Field(default=Decimal("1.00"), gt=Decimal("0.00"))
    unit_price: Decimal = Field(..., gt=Decimal("0.00"))
    revenue_account: int | None = None


class InvoiceItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    invoice_item_id: str
    invoice_id: str
    line_no: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    revenue_account: int


class InvoiceCreateRequest(BaseModel):
    invoice_id: str | None = None
    invoice_number: str | None = None
    client_id: str
    invoice_date: date
    due_date: date | None = None
    service_line_account: int | None = None
    gst_rate_percent: Decimal | None = None
    po_number: str | None = None
    created_by: str | None = "U-0099"
    items: list[InvoiceItemInput] = Field(..., min_length=1)


class InvoicePaymentCreateRequest(BaseModel):
    payment_id: str | None = None
    payment_date: date
    amount: Decimal = Field(..., gt=Decimal("0.00"))
    payment_mode: str = Field(default="NEFT", max_length=32)
    reference_no: str | None = None
    received_by: str | None = "U-0099"


class InvoicePaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_id: str
    invoice_id: str
    payment_date: date
    amount: Decimal
    payment_mode: str
    reference_no: str | None = None
    received_by: str | None = None
    ledger_entry_id: str | None = None


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    invoice_id: str
    invoice_number: str
    client_id: str
    invoice_date: date
    due_date: date
    service_line_account: int
    currency: str
    subtotal: Decimal
    gst_rate_percent: Decimal
    gst_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    status: str
    last_payment_date: date | None = None
    po_number: str | None = None
    carried_in_from_prior_period: str
    created_by: str | None = None
    created_at: str | None = None
    ledger_entry_id: str | None = None
    items: list[InvoiceItemRead] = []
    payments: list[InvoicePaymentRead] = []


class ClientReceivableItem(BaseModel):
    client_id: str
    client_name: str
    client_type: str
    open_invoices_count: int
    total_invoiced_open: Decimal
    total_paid_on_open: Decimal
    balance_due: Decimal


class ReceivablesReportRead(BaseModel):
    as_of_date: date
    total_open_invoices: int
    total_open_receivables: Decimal
    ledger_account_1100_balance: Decimal
    reconciled_difference: Decimal
    is_reconciled: bool
    clients: list[ClientReceivableItem]
