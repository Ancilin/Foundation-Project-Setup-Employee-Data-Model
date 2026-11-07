"""Configurable Tax Rules (Slabs, Tax Parameters, Statutory Rates) & Monthly Statutory Reports (PF, ESI, TDS) HTTP routes (Task 14 / LF-14)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.security import ensure_self_or_hr_admin, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.tax import (
    AnnualTaxBreakdownRead,
    ESIMonthlyReportRead,
    PFMonthlyReportRead,
    SlabChangeRerunRequest,
    SlabChangeRerunResultRead,
    StatutoryAllMonthsSummaryRead,
    StatutoryRateRead,
    StatutoryRateUpdateRequest,
    TDSMonthlyReportRead,
    TaxParameterRead,
    TaxParameterUpdateRequest,
    TaxSlabCreateRequest,
    TaxSlabRead,
    TaxSlabUpdateRequest,
)
from app.services import tax_service

router = APIRouter(prefix="/tax", tags=["Taxes & Statutory Reports (Task 14)"])


@router.get("/slabs", response_model=list[TaxSlabRead])
def list_slabs(
    financial_year: str | None = Query(default=None, description="Filter by FY, e.g. FY2025-26 or FY2026-27"),
    regime: str | None = Query(default=None, description="Filter by tax regime, e.g. NEW or OLD"),
    _current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
    db: Session = Depends(get_db),
):
    """List configurable tax slabs from the database."""
    return tax_service.list_tax_slabs(db, financial_year=financial_year, regime=regime)


@router.post("/slabs", response_model=TaxSlabRead, status_code=status.HTTP_201_CREATED)
def create_slab(
    payload: TaxSlabCreateRequest,
    _current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Create a new tax slab (Admin only)."""
    return tax_service.create_tax_slab(
        session=db,
        slab_id=payload.slab_id,
        financial_year=payload.financial_year,
        income_from=payload.income_from,
        income_to=payload.income_to,
        rate_percent=payload.rate_percent,
        effective_from=payload.effective_from,
        regime=payload.regime,
        note=payload.note,
    )


@router.patch("/slabs/{slab_id}", response_model=TaxSlabRead)
@router.put("/slabs/{slab_id}", response_model=TaxSlabRead)
def update_slab(
    slab_id: str,
    payload: TaxSlabUpdateRequest,
    _current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Update a tax slab's rate_percent, bounds, or effective_from date (Admin only)."""
    return tax_service.update_tax_slab(
        session=db,
        slab_id=slab_id,
        rate_percent=payload.rate_percent,
        income_from=payload.income_from,
        income_to=payload.income_to,
        effective_from=payload.effective_from,
        note=payload.note,
    )


@router.get("/parameters", response_model=list[TaxParameterRead])
def list_parameters(
    _current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
    db: Session = Depends(get_db),
):
    """List configurable tax parameters (standard_deduction, rebate_threshold_taxable, health_education_cess_percent)."""
    return tax_service.list_tax_parameters(db)


@router.patch("/parameters/{parameter}", response_model=TaxParameterRead)
def update_parameter(
    parameter: str,
    payload: TaxParameterUpdateRequest,
    _current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Update a tax parameter (Admin only)."""
    return tax_service.update_tax_parameter(
        session=db,
        parameter=parameter,
        value=payload.value,
        note=payload.note,
    )


@router.get("/statutory-rates", response_model=list[StatutoryRateRead])
def list_statutory_rates(
    _current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
    db: Session = Depends(get_db),
):
    """List configurable statutory rates (PF, ESI, Professional Tax, Overtime)."""
    return tax_service.list_statutory_rates(db)


@router.patch("/statutory-rates/{parameter}", response_model=StatutoryRateRead)
def update_statutory_rate(
    parameter: str,
    payload: StatutoryRateUpdateRequest,
    _current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Update a statutory rate (Admin only)."""
    return tax_service.update_statutory_rate(
        session=db,
        parameter=parameter,
        value=payload.value,
        effective_from=payload.effective_from,
        note=payload.note,
    )


@router.get("/breakdown/{employee_id}/{month}", response_model=AnnualTaxBreakdownRead)
def get_tax_breakdown(
    employee_id: str,
    month: str,
    current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
    db: Session = Depends(get_db),
):
    """Return the step-by-step annual taxable income, slab tax, Section 87A rebate, 4% cess,
    and monthly TDS (/ 12) for an employee in a given month (employees may view only their own).
    """
    ensure_self_or_hr_admin(current_user, employee_id)
    return tax_service.get_employee_tax_breakdown(db, employee_id=employee_id, month=month)


@router.post("/slabs/rerun-demo", response_model=SlabChangeRerunResultRead)
def change_slab_and_rerun_demo(
    payload: SlabChangeRerunRequest,
    _current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Admin-only demonstration endpoint: changes a slab rate, reruns one month, returns before/after
    tax for one employee and the entire run, verifies past months are untouched, and optionally restores the slab.
    """
    return tax_service.change_slab_and_rerun_month(
        session=db,
        slab_id=payload.slab_id,
        new_rate_percent=payload.new_rate_percent,
        month=payload.month,
        employee_id=payload.employee_id,
        revert_after_demo=payload.revert_after_demo,
    )


@router.get("/reports/pf", response_model=PFMonthlyReportRead)
def get_pf_report(
    month: str = Query(default="2026-09", description="Payroll month YYYY-MM or run_id PR-YYYY-MM"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Generate the monthly Provident Fund (PF) statutory report and reconcile totals against payroll data."""
    return tax_service.get_monthly_pf_report(db, month=month)


@router.get("/reports/esi", response_model=ESIMonthlyReportRead)
def get_esi_report(
    month: str = Query(default="2026-09", description="Payroll month YYYY-MM or run_id PR-YYYY-MM"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Generate the monthly Employees' State Insurance (ESI) statutory report and reconcile totals against payroll data."""
    return tax_service.get_monthly_esi_report(db, month=month)


@router.get("/reports/tds", response_model=TDSMonthlyReportRead)
def get_tds_report(
    month: str = Query(default="2026-09", description="Payroll month YYYY-MM or run_id PR-YYYY-MM"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Generate the monthly Income Tax (TDS) statutory report and reconcile totals against payroll data."""
    return tax_service.get_monthly_tds_report(db, month=month)


@router.get("/reports/summary", response_model=StatutoryAllMonthsSummaryRead)
def get_all_months_statutory_reconciliation(
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Reconcile PF, ESI, Professional Tax, and TDS report totals across all 18 payroll months against payroll data."""
    return tax_service.get_all_months_statutory_summary(db)
