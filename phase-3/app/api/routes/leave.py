"""Leave HTTP routes: holidays, leave types, balances, apply, approve, and reject (LF-06, LF-13)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.security import ensure_self_or_hr_admin, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.leave import (
    HolidayRead,
    LeaveApplyRequest,
    LeaveBalanceRead,
    LeaveDecisionRequest,
    LeaveRequestRead,
    LeaveTypeRead,
)
from app.services import leave_service

router = APIRouter(prefix="/leave", tags=["Leave"])


@router.get("/holidays", response_model=list[HolidayRead])
def list_company_holidays(
    _current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
    db: Session = Depends(get_db),
):
    """List all company holidays."""
    return leave_service.list_holidays(db)


@router.get("/types", response_model=list[LeaveTypeRead])
def list_leave_types(
    _current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
    db: Session = Depends(get_db),
):
    """List all leave types and quotas."""
    return leave_service.list_leave_types(db)


@router.get("/balances/{employee_id}", response_model=LeaveBalanceRead)
def get_employee_leave_balance(
    employee_id: str,
    current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
    db: Session = Depends(get_db),
):
    """Retrieve the current leave balance for an employee (employees may read only their own)."""
    ensure_self_or_hr_admin(current_user, employee_id)
    return leave_service.get_leave_balance(db, employee_id)


@router.get("/requests", response_model=list[LeaveRequestRead])
def list_leave_requests(
    employee_id: str | None = Query(None, description="Filter by employee_id"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
    db: Session = Depends(get_db),
):
    """List leave requests with optional filters (employees may read only their own)."""
    if (current_user.role or "").upper() == "EMPLOYEE":
        if employee_id and employee_id != current_user.employee_id:
            ensure_self_or_hr_admin(current_user, employee_id)
        employee_id = current_user.employee_id
    return leave_service.list_leave_requests(db, employee_id=employee_id, status=status_filter)


@router.post("/requests", response_model=LeaveRequestRead, status_code=status.HTTP_201_CREATED)
def apply_for_leave(
    payload: LeaveApplyRequest,
    current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
    db: Session = Depends(get_db),
):
    """Submit a new leave request (employees may apply only for their own employee_id)."""
    ensure_self_or_hr_admin(current_user, payload.employee_id)
    return leave_service.apply_leave(db, payload)


@router.post("/requests/{leave_request_id}/approve", response_model=LeaveRequestRead)
def approve_leave_request(
    leave_request_id: str,
    payload: LeaveDecisionRequest,
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Approve a pending leave request and deduct from the employee's balance (HR and Admin only)."""
    return leave_service.approve_leave(
        db,
        leave_request_id=leave_request_id,
        approver_id=payload.approver_id,
        decided_on=payload.decided_on,
    )


@router.post("/requests/{leave_request_id}/reject", response_model=LeaveRequestRead)
def reject_leave_request(
    leave_request_id: str,
    payload: LeaveDecisionRequest,
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Reject a pending leave request without deducting balance (HR and Admin only)."""
    return leave_service.reject_leave(
        db,
        leave_request_id=leave_request_id,
        approver_id=payload.approver_id,
        decided_on=payload.decided_on,
    )
