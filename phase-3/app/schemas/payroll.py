"""Pydantic schemas for Payroll calculation, Payroll Runs, Idempotent Approval & Ledger Posting, Reversal, and Reconciliation (LF-07, LF-12)."""

from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ledger import JournalEntryRead


class PayrollCalculateRequest(BaseModel):
    employee_id: str = Field(..., min_length=1, max_length=10)
    month: str = Field(..., description="Payroll month in YYYY-MM format, e.g. 2025-04")
    variable_pay: Decimal = Decimal("0.00")
    variable_pay_type: str | None = None
    other_deductions: Decimal = Decimal("0.00")


class PayrollItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    employee_id: str
    period_start: date
    period_end: date
    department_id: str
    role_id: str
    calendar_days: int
    days_employed: int
    lop_days: Decimal
    payable_days: Decimal
    monthly_fixed_gross: Decimal
    basic: Decimal
    hra: Decimal
    conveyance: Decimal
    medical: Decimal
    special_allowance: Decimal
    earned_fixed_pay: Decimal
    overtime_hours_paid: Decimal
    overtime_pay: Decimal
    variable_pay: Decimal
    variable_pay_type: str | None = None
    gross_pay: Decimal
    pf_employee: Decimal
    esi_employee: Decimal
    professional_tax: Decimal
    tds: Decimal
    other_deductions: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    pf_employer: Decimal
    esi_employer: Decimal
    employer_cost: Decimal
    calculation_note: str | None = None


class PayrollRunCreateRequest(BaseModel):
    month: str = Field(..., description="Payroll month in YYYY-MM format, e.g. 2025-04")
    run_id: str | None = None
    pay_date: date | None = None
    run_by: str = Field(default="U-0237", min_length=1, max_length=16)
    idempotency_key: str | None = None


class PayrollRunProcessRequest(BaseModel):
    run_by: str | None = "U-0237"


class PayrollRunApproveRequest(BaseModel):
    approved_by: str = Field(default="U-0099", min_length=1, max_length=16)
    idempotency_key: str | None = None
    simulate_ledger_failure: bool = False


class PayrollRunPayRequest(BaseModel):
    pay_date: date | None = None
    paid_by: str = Field(default="U-0099", min_length=1, max_length=16)


class PayrollRunReverseRequest(BaseModel):
    reversal_date: date | None = None
    reversed_by: str = Field(default="U-0099", min_length=1, max_length=16)
    reason: str | None = None


class PayrollRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    period_start: date
    period_end: date
    pay_date: date | None = None
    employees_paid: int
    total_gross: Decimal
    total_deductions: Decimal
    total_net: Decimal
    total_employer_contributions: Decimal
    total_employer_cost: Decimal
    status: str
    run_by: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    idempotency_key: str | None = None
    journal_entry_id: str | None = None
    calculation_version: str | None = None


class PayrollRunDetailRead(PayrollRunRead):
    ledger_employer_cost_5001_5005: Decimal = Decimal("0.00")
    employer_cost_difference: Decimal = Decimal("0.00")
    idempotent_replay: bool | None = None
    reversal_journal_entry_id: str | None = None
    payment_reversal_journal_entry_id: str | None = None
    journal_entry: JournalEntryRead | None = None
    reversal_journal_entry: JournalEntryRead | None = None


class PayrollReconciliationItem(BaseModel):
    run_id: str
    month: str
    status: str
    employees_paid: int
    idempotency_key: str | None = None
    journal_entry_id: str | None = None
    total_gross: Decimal
    total_employer_contributions: Decimal
    run_employer_cost: Decimal
    ledger_accounts_5001_5005_debit: Decimal
    difference: Decimal
    matches: bool


class PayrollReconciliationReportRead(BaseModel):
    total_runs: int
    all_months_match: bool
    total_run_employer_cost: Decimal
    total_ledger_employer_cost: Decimal
    largest_monthly_difference: Decimal
    runs: list[PayrollReconciliationItem]
