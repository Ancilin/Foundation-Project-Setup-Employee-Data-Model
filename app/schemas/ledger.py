"""Pydantic schemas for Double-Entry Ledger, Chart of Accounts, Reversals, and Account Balances (LF-09)."""

from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class ChartOfAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_code: int
    account_name: str
    account_type: str
    normal_balance: str
    parent_code: int | None = None
    is_group: str
    statement: str
    is_active: str


class JournalLineInput(BaseModel):
    account_code: int = Field(..., description="Account code from chart_of_accounts (e.g. 5001, 2100)")
    debit: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    credit: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    cost_center_department_id: str | None = None
    line_description: str | None = None


class JournalLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line_id: str
    entry_id: str
    line_no: int
    account_code: int
    debit: Decimal
    credit: Decimal
    cost_center_department_id: str | None = None
    line_description: str | None = None


class JournalEntryCreateRequest(BaseModel):
    entry_id: str | None = None
    entry_date: date
    description: str = Field(..., min_length=1, max_length=255)
    source_type: str = Field(default="MANUAL", max_length=32)
    source_id: str = Field(default="MANUAL-001", max_length=32)
    created_by: str | None = Field(default="U-0099", max_length=32)
    reversal_of_source_id: str | None = None
    lines: list[JournalLineInput] = Field(..., min_length=2)


class JournalEntryUpdateRequest(BaseModel):
    description: str | None = None
    entry_date: date | None = None


class JournalEntryReverseRequest(BaseModel):
    reversal_date: date | None = None
    description: str | None = None
    created_by: str | None = "U-0099"


class JournalEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entry_id: str
    entry_date: date
    posting_period: str
    financial_year: str
    description: str
    source_type: str
    source_id: str
    status: str
    total_debit: Decimal
    total_credit: Decimal
    reversal_of_source_id: str | None = None
    created_by: str | None = None
    created_at: str | None = None
    lines: list[JournalLineRead] = []


class AccountBalanceRead(BaseModel):
    account_code: int
    account_name: str
    account_type: str
    normal_balance: str
    as_of_date: date
    total_debit: Decimal
    total_credit: Decimal
    debit_minus_credit: Decimal
    balance: Decimal
