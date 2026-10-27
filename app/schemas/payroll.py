"""Pydantic schemas for Payroll calculation and items (LF-07)."""

from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


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
