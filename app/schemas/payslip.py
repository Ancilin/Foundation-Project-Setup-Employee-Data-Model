"""Pydantic schemas for Payslip data and PDF generation (LF-08)."""

from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class PayslipLineItem(BaseModel):
    label: str
    amount: Decimal
    formatted_amount: str


class PayslipYTD(BaseModel):
    financial_year: str
    months_included: int
    ytd_gross_pay: Decimal
    ytd_gross_pay_formatted: str
    ytd_total_deductions: Decimal
    ytd_total_deductions_formatted: str
    ytd_tds: Decimal
    ytd_tds_formatted: str
    ytd_pf_employee: Decimal
    ytd_pf_employee_formatted: str
    ytd_net_pay: Decimal
    ytd_net_pay_formatted: str


class PayslipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_name: str
    company_address: str
    run_id: str
    month: str
    period_start: date
    period_end: date
    pay_date: date | None = None
    employee_id: str
    employee_name: str
    work_email: str
    department_id: str
    department_name: str
    role_id: str
    role_title: str
    employment_type: str
    work_location: str
    calendar_days: int
    days_employed: int
    lop_days: Decimal
    payable_days: Decimal
    overtime_hours_paid: Decimal
    monthly_fixed_gross: Decimal
    monthly_fixed_gross_formatted: str
    basic: Decimal
    basic_formatted: str
    hra: Decimal
    hra_formatted: str
    conveyance: Decimal
    conveyance_formatted: str
    medical: Decimal
    medical_formatted: str
    special_allowance: Decimal
    special_allowance_formatted: str
    earned_fixed_pay: Decimal
    earned_fixed_pay_formatted: str
    overtime_pay: Decimal
    overtime_pay_formatted: str
    variable_pay: Decimal
    variable_pay_formatted: str
    variable_pay_type: str | None = None
    gross_pay: Decimal
    gross_pay_formatted: str
    pf_employee: Decimal
    pf_employee_formatted: str
    esi_employee: Decimal
    esi_employee_formatted: str
    professional_tax: Decimal
    professional_tax_formatted: str
    tds: Decimal
    tds_formatted: str
    other_deductions: Decimal
    other_deductions_formatted: str
    total_deductions: Decimal
    total_deductions_formatted: str
    net_pay: Decimal
    net_pay_formatted: str
    net_pay_in_words: str
    pf_employer: Decimal
    pf_employer_formatted: str
    esi_employer: Decimal
    esi_employer_formatted: str
    employer_cost: Decimal
    employer_cost_formatted: str
    earnings: list[PayslipLineItem]
    deductions: list[PayslipLineItem]
    ytd_summary: PayslipYTD
    calculation_note: str
