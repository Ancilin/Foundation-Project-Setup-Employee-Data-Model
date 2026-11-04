"""Pydantic schemas for Vendors, Expense Bills, Approval & Payment workflows, Spend Reports, and Duplicate Detection (LF-11)."""

from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class VendorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vendor_id: str
    vendor_name: str
    primary_expense_account: int
    payment_terms_days: int
    city: str
    gst_registration: str | None = None
    is_active: str


class ExpenseCreateRequest(BaseModel):
    expense_id: str | None = None
    expense_date: date
    vendor_id: str
    category_account: int | None = None
    bill_reference: str | None = None
    description: str = Field(..., min_length=1, max_length=255)
    department_id: str = Field(default="D09", min_length=2, max_length=16)
    amount_excl_gst: Decimal = Field(..., gt=Decimal("0.00"))
    gst_rate_percent: Decimal = Field(default=Decimal("18.00"), ge=Decimal("0.00"))
    due_date: date | None = None
    submitted_by: str = Field(..., min_length=1, max_length=32)
    allow_duplicate: bool = False


class ExpenseApproveRequest(BaseModel):
    approved_by: str = Field(..., min_length=1, max_length=32)


class ExpensePaymentRequest(BaseModel):
    paid_date: date
    payment_mode: str = Field(default="NEFT", min_length=1, max_length=32)
    paid_by: str | None = "U-0099"


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    expense_id: str
    expense_date: date
    category_account: int
    vendor_id: str
    bill_reference: str
    description: str
    department_id: str
    amount_excl_gst: Decimal
    gst_rate_percent: Decimal
    gst_amount: Decimal
    total_amount: Decimal
    due_date: date
    paid_date: date | None = None
    status: str
    payment_mode: str | None = None
    submitted_by: str
    approved_by: str | None = None
    ledger_entry_id: str | None = None
    payment_ledger_entry_id: str | None = None


class VendorSpendItem(BaseModel):
    vendor_id: str
    vendor_name: str
    primary_expense_account: int
    bills_count: int
    amount_excl_gst: Decimal
    gst_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    unpaid_amount: Decimal


class MonthlySpendItem(BaseModel):
    month: str
    bills_count: int
    amount_excl_gst: Decimal
    gst_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    unpaid_amount: Decimal


class VendorMonthlySpendItem(BaseModel):
    month: str
    vendor_id: str
    vendor_name: str
    bills_count: int
    amount_excl_gst: Decimal
    gst_amount: Decimal
    total_amount: Decimal


class SpendReportRead(BaseModel):
    total_bills: int
    total_amount_excl_gst: Decimal
    total_gst_amount: Decimal
    total_spend_amount: Decimal
    total_paid_amount: Decimal
    total_unpaid_payable: Decimal
    ledger_account_2001_balance: Decimal
    payable_reconciled_difference: Decimal
    is_payable_reconciled: bool
    by_vendor: list[VendorSpendItem]
    by_month: list[MonthlySpendItem]
    by_vendor_month: list[VendorMonthlySpendItem]


class MonthlyCsvComparisonItem(BaseModel):
    month: str
    db_bills_count: int
    csv_bills_count: int
    db_amount_excl_gst: Decimal
    csv_amount_excl_gst: Decimal
    ledger_expense_debit: Decimal
    db_gst_amount: Decimal
    csv_gst_amount: Decimal
    db_total_amount: Decimal
    csv_total_amount: Decimal
    difference_excl_gst: Decimal
    difference_total: Decimal
    matches: bool


class MonthlyReconciliationReportRead(BaseModel):
    total_months: int
    all_months_match: bool
    total_db_amount_excl_gst: Decimal
    total_csv_amount_excl_gst: Decimal
    total_ledger_expense_debit: Decimal
    total_db_total_amount: Decimal
    total_csv_total_amount: Decimal
    max_monthly_difference: Decimal
    months: list[MonthlyCsvComparisonItem]


class DuplicateCheckRequest(BaseModel):
    vendor_id: str
    expense_date: date
    amount_excl_gst: Decimal | None = None
    total_amount: Decimal | None = None
    bill_reference: str | None = None
    window_days: int = Field(default=0, ge=0, le=30)


class DuplicateCandidateItem(BaseModel):
    expense_id: str
    vendor_id: str
    expense_date: date
    bill_reference: str
    amount_excl_gst: Decimal
    total_amount: Decimal
    status: str
    reason: str


class DuplicatePairItem(BaseModel):
    first_expense_id: str
    second_expense_id: str
    vendor_id: str
    expense_date_1: date
    expense_date_2: date
    amount_excl_gst: Decimal
    total_amount: Decimal
    bill_reference_1: str
    bill_reference_2: str
    reason: str


class DuplicateDetectionReportRead(BaseModel):
    duplicate_groups_count: int
    duplicates: list[DuplicatePairItem]
