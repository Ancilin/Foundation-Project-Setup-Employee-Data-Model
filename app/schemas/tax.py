"""Pydantic schemas for Configurable Tax Rules (Slabs, Tax Parameters, Statutory Rates),
Annual Tax Breakdown, Slab-Change Rerun Simulation, and Monthly Statutory Reports (PF, ESI, TDS) (Task 14 / LF-14).
"""

from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class TaxSlabRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slab_id: str
    regime: str
    financial_year: str
    income_from: Decimal
    income_to: Decimal | None = None
    rate_percent: Decimal
    effective_from: date
    note: str | None = None


class TaxSlabCreateRequest(BaseModel):
    slab_id: str = Field(..., min_length=2, max_length=16, examples=["TS-015"])
    regime: str = Field(default="NEW", min_length=2, max_length=16)
    financial_year: str = Field(..., min_length=4, max_length=16, examples=["FY2026-27"])
    income_from: Decimal = Field(..., ge=Decimal("0.00"))
    income_to: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    rate_percent: Decimal = Field(..., ge=Decimal("0.00"), le=Decimal("100.00"))
    effective_from: date = Field(..., examples=["2026-04-01"])
    note: str | None = None


class TaxSlabUpdateRequest(BaseModel):
    rate_percent: Decimal | None = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    income_from: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    income_to: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    effective_from: date | None = None
    note: str | None = None


class TaxParameterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parameter: str
    value: Decimal
    note: str | None = None


class TaxParameterUpdateRequest(BaseModel):
    value: Decimal = Field(..., ge=Decimal("0.00"))
    note: str | None = None


class StatutoryRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parameter: str
    value: Decimal
    unit: str
    note: str | None = None
    effective_from: date


class StatutoryRateUpdateRequest(BaseModel):
    value: Decimal = Field(..., ge=Decimal("0.00"))
    effective_from: date | None = None
    note: str | None = None


class SlabBandBreakdownRead(BaseModel):
    slab_id: str | None = None
    income_from: Decimal
    income_to: Decimal | None = None
    rate_percent: Decimal
    taxable_in_slab: Decimal
    tax_in_slab: Decimal


class AnnualTaxBreakdownRead(BaseModel):
    employee_id: str | None = None
    month: str | None = None
    financial_year: str | None = None
    regime: str = "NEW"
    monthly_fixed_gross: Decimal
    annual_gross_income: Decimal
    standard_deduction: Decimal
    annual_taxable_income: Decimal
    rebate_threshold: Decimal
    raw_slab_tax: Decimal
    rebate_87a_amount: Decimal
    tax_after_rebate: Decimal
    cess_percent: Decimal
    cess_amount: Decimal
    annual_total_tax: Decimal
    monthly_tds: Decimal
    slab_breakdown: list[SlabBandBreakdownRead]


class SlabChangeRerunRequest(BaseModel):
    slab_id: str = Field(default="TS-011", description="Slab ID to modify, e.g. TS-011 (12L-16L in FY2026-27)")
    new_rate_percent: Decimal = Field(default=Decimal("20.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    month: str = Field(default="2026-09", description="Target payroll month YYYY-MM to rerun")
    employee_id: str = Field(default="EMP-0006", description="Employee ID to highlight before/after tax")
    revert_after_demo: bool = Field(
        default=True,
        description="If True, automatically restores the original slab rate and reruns the month back after capturing before/after evidence",
    )


class EmployeeTaxComparisonRead(BaseModel):
    employee_id: str
    employee_name: str
    month: str
    monthly_fixed_gross: Decimal
    annual_taxable_income: Decimal
    old_slab_rate_percent: Decimal
    new_slab_rate_percent: Decimal
    before_annual_tax: Decimal
    after_annual_tax: Decimal
    before_monthly_tds: Decimal
    after_monthly_tds: Decimal
    monthly_tds_difference: Decimal
    before_net_pay: Decimal
    after_net_pay: Decimal


class SlabChangeRerunResultRead(BaseModel):
    slab_id: str
    financial_year: str
    month_rerun: str
    run_id: str
    old_rate_percent: Decimal
    new_rate_percent: Decimal
    run_total_tds_before: Decimal
    run_total_tds_after: Decimal
    run_total_tds_difference: Decimal
    run_total_net_before: Decimal
    run_total_net_after: Decimal
    past_months_untouched_verified: bool
    sample_past_run_id: str
    sample_past_run_tds_before: Decimal
    sample_past_run_tds_after: Decimal
    reverted_to_original: bool
    employee_comparison: EmployeeTaxComparisonRead


class PFEmployeeReportRow(BaseModel):
    employee_id: str
    employee_name: str
    department_id: str
    monthly_fixed_gross: Decimal
    earned_basic: Decimal
    pf_wage: Decimal
    pf_employee: Decimal
    pf_employer: Decimal
    total_pf: Decimal


class PFMonthlyReportRead(BaseModel):
    report_type: str = "PROVIDENT_FUND_MONTHLY"
    month: str
    run_id: str
    pf_employee_rate_percent: Decimal
    pf_employer_rate_percent: Decimal
    pf_wage_ceiling: Decimal
    employees_covered: int
    total_earned_basic: Decimal
    total_pf_wage: Decimal
    total_pf_employee: Decimal
    total_pf_employer: Decimal
    total_pf_contribution: Decimal
    payroll_pf_employee_sum: Decimal
    payroll_pf_employer_sum: Decimal
    difference: Decimal
    is_reconciled: bool
    rows: list[PFEmployeeReportRow]


class ESIEmployeeReportRow(BaseModel):
    employee_id: str
    employee_name: str
    department_id: str
    monthly_fixed_gross: Decimal
    gross_pay: Decimal
    esi_employee: Decimal
    esi_employer: Decimal
    total_esi: Decimal


class ESIMonthlyReportRead(BaseModel):
    report_type: str = "ESI_MONTHLY"
    month: str
    run_id: str
    esi_employee_rate_percent: Decimal
    esi_employer_rate_percent: Decimal
    esi_wage_limit: Decimal
    employees_covered: int
    total_gross_covered: Decimal
    total_esi_employee: Decimal
    total_esi_employer: Decimal
    total_esi_contribution: Decimal
    payroll_esi_employee_sum: Decimal
    payroll_esi_employer_sum: Decimal
    difference: Decimal
    is_reconciled: bool
    rows: list[ESIEmployeeReportRow]


class TDSEmployeeReportRow(BaseModel):
    employee_id: str
    employee_name: str
    department_id: str
    monthly_fixed_gross: Decimal
    gross_pay: Decimal
    annual_taxable_income: Decimal
    tds: Decimal


class TDSMonthlyReportRead(BaseModel):
    report_type: str = "TDS_MONTHLY"
    month: str
    run_id: str
    financial_year: str
    standard_deduction: Decimal
    rebate_threshold: Decimal
    cess_percent: Decimal
    employees_taxed: int
    total_employees_in_run: int
    total_gross_pay: Decimal
    total_tds: Decimal
    payroll_tds_sum: Decimal
    difference: Decimal
    is_reconciled: bool
    rows: list[TDSEmployeeReportRow]


class StatutoryMonthSummaryRow(BaseModel):
    month: str
    run_id: str
    employees_paid: int
    pf_employee: Decimal
    pf_employer: Decimal
    esi_employee: Decimal
    esi_employer: Decimal
    professional_tax: Decimal
    tds: Decimal
    report_total_statutory: Decimal
    payroll_total_statutory: Decimal
    difference: Decimal
    is_reconciled: bool


class StatutoryAllMonthsSummaryRead(BaseModel):
    months_checked: int
    all_reconciled: bool
    max_abs_difference: Decimal
    grand_total_pf_employee: Decimal
    grand_total_pf_employer: Decimal
    grand_total_esi_employee: Decimal
    grand_total_esi_employer: Decimal
    grand_total_professional_tax: Decimal
    grand_total_tds: Decimal
    months: list[StatutoryMonthSummaryRow]
