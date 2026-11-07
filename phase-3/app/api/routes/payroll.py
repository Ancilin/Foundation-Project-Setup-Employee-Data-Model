"""Payroll HTTP routes: employee month calculation (LF-07), Payroll Run lifecycle,
idempotent auto-posting to ledger, reversal, 18-month Check 2 reconciliation (LF-12), and RBAC (LF-13).
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.payroll import (
    PayrollCalculateRequest,
    PayrollItemRead,
    PayrollReconciliationReportRead,
    PayrollRunApproveRequest,
    PayrollRunCreateRequest,
    PayrollRunDetailRead,
    PayrollRunPayRequest,
    PayrollRunProcessRequest,
    PayrollRunRead,
    PayrollRunReverseRequest,
)
from app.services import payroll_service

router = APIRouter(prefix="/payroll", tags=["Payroll"])


@router.post("/calculate", response_model=PayrollItemRead)
def calculate_payroll_for_employee_month(
    payload: PayrollCalculateRequest,
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Calculate full gross-to-net pay for an employee and month (LF-07)."""
    return payroll_service.calculate_employee_month_from_db(
        session=db,
        employee_id=payload.employee_id,
        month=payload.month,
        variable_pay=payload.variable_pay,
        variable_pay_type=payload.variable_pay_type,
        other_deductions=payload.other_deductions,
    )


@router.get("/runs", response_model=list[PayrollRunRead])
def get_payroll_runs(
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """List all payroll runs across all months."""
    return payroll_service.list_payroll_runs(db)


@router.post("/runs", response_model=PayrollRunRead, status_code=status.HTTP_201_CREATED)
def create_draft_payroll_run(
    payload: PayrollRunCreateRequest,
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Create a payroll run in DRAFT status (idempotent by run_id and idempotency_key)."""
    return payroll_service.create_payroll_run(
        session=db,
        month=payload.month,
        run_id=payload.run_id,
        pay_date=payload.pay_date,
        run_by=payload.run_by,
        idempotency_key=payload.idempotency_key,
    )


@router.get("/runs/reconciliation", response_model=PayrollReconciliationReportRead)
def get_payroll_ledger_reconciliation(
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Reconcile all payroll runs against ledger accounts 5001..5005 (Check 2)."""
    return payroll_service.reconcile_all_payroll_runs_with_ledger(db)


@router.get("/runs/{run_id}", response_model=PayrollRunDetailRead)
def get_payroll_run(
    run_id: str,
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Retrieve a payroll run with its journal_entry_id, idempotency_key, and linked journal entry lines."""
    return payroll_service.get_payroll_run_with_details(db, run_id=run_id)


@router.post("/runs/{run_id}/process", response_model=PayrollRunRead)
def process_run(
    run_id: str,
    payload: PayrollRunProcessRequest | None = None,
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Process a DRAFT payroll run using the Task 7 engine for every eligible employee."""
    run_by = payload.run_by if payload else None
    return payroll_service.process_payroll_run(db, run_id=run_id, run_by=run_by)


@router.post("/runs/{run_id}/approve", response_model=PayrollRunDetailRead)
def approve_and_post_run(
    run_id: str,
    payload: PayrollRunApproveRequest | None = None,
    _current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Approve a PROCESSED payroll run and post ONE balanced journal entry to the ledger.
    Idempotent: a double click returns the existing posting without posting twice.
    """
    req = payload or PayrollRunApproveRequest()
    return payroll_service.approve_payroll_run(
        session=db,
        run_id=run_id,
        approved_by=req.approved_by,
        idempotency_key=req.idempotency_key,
        simulate_ledger_failure=req.simulate_ledger_failure,
    )


@router.post("/runs/{run_id}/pay", response_model=PayrollRunDetailRead)
def pay_run(
    run_id: str,
    payload: PayrollRunPayRequest | None = None,
    _current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Mark an APPROVED payroll run as PAID and post salary disbursement to the ledger."""
    req = payload or PayrollRunPayRequest()
    return payroll_service.pay_payroll_run(
        session=db,
        run_id=run_id,
        pay_date=req.pay_date,
        paid_by=req.paid_by,
    )


@router.post("/runs/{run_id}/reverse", response_model=PayrollRunDetailRead)
def reverse_run(
    run_id: str,
    payload: PayrollRunReverseRequest | None = None,
    _current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Reverse/cancel a posted payroll run and post an official reversing journal entry."""
    req = payload or PayrollRunReverseRequest()
    return payroll_service.reverse_payroll_run(
        session=db,
        run_id=run_id,
        reversal_date=req.reversal_date,
        reversed_by=req.reversed_by,
        reason=req.reason,
    )
