"""Leave service: apply, approve, reject, balance updates, and holiday/weekend exclusion (LF-06)."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, ConflictError, NotFoundError, ValidationError
from app.models.employee import Employee
from app.models.leave import Holiday, LeaveBalance, LeaveRequest, LeaveType
from app.schemas.leave import LeaveApplyRequest
from app.services.attendance_service import count_working_days


def list_holidays(session: Session) -> list[Holiday]:
    """List all company holidays ordered by date."""
    return list(session.scalars(select(Holiday).order_by(Holiday.holiday_date)).all())


def list_leave_types(session: Session) -> list[LeaveType]:
    """List all configured leave types."""
    return list(session.scalars(select(LeaveType).order_by(LeaveType.leave_type_code)).all())


def get_or_create_leave_balance(session: Session, employee_id: str) -> LeaveBalance:
    """Retrieve an employee's leave balance, creating a default FY2026-27 balance if absent."""
    emp = session.get(Employee, employee_id)
    if not emp:
        raise NotFoundError(f"Employee '{employee_id}' not found")

    bal = session.get(LeaveBalance, employee_id)
    if not bal:
        bal = LeaveBalance(
            employee_id=employee_id,
            as_of_date=date(2026, 9, 30),
            financial_year="FY2026-27",
            cl_entitlement=Decimal("12.00"),
            cl_used=Decimal("0.00"),
            cl_balance=Decimal("12.00"),
            sl_entitlement=Decimal("12.00"),
            sl_used=Decimal("0.00"),
            sl_balance=Decimal("12.00"),
            el_used_fy=Decimal("0.00"),
            el_balance=Decimal("15.00"),
            pending_days=Decimal("0.00"),
        )
        session.add(bal)
        session.commit()
        session.refresh(bal)
    return bal


def get_leave_balance(session: Session, employee_id: str) -> LeaveBalance:
    """Get leave balance for an employee."""
    return get_or_create_leave_balance(session, employee_id)


def _available_balance_for_type(
    balance: LeaveBalance,
    leave_type: LeaveType,
) -> Decimal | None:
    """Return available balance for the given leave type, or None if unlimited (LOP)."""
    code = leave_type.leave_type_code.upper()
    if code == "CL":
        return Decimal(str(balance.cl_balance))
    if code == "SL":
        return Decimal(str(balance.sl_balance))
    if code == "EL":
        return Decimal(str(balance.el_balance))
    if code in ("ML", "BL"):
        return Decimal(str(leave_type.annual_quota_days))
    if code == "LOP":
        return None
    return Decimal(str(leave_type.annual_quota_days))


def apply_leave(
    session: Session,
    payload: LeaveApplyRequest | dict[str, Any],
    auto_reject_insufficient: bool = False,
) -> LeaveRequest:
    """Apply for leave:
    - Skips weekends and company holidays when counting working days.
    - Supports half-day leave (0.5 working day).
    - Rejects the request when leave balance is insufficient.
    """
    data = payload.model_dump() if isinstance(payload, LeaveApplyRequest) else dict(payload)
    employee_id = data["employee_id"]
    leave_type_code = str(data["leave_type_code"]).upper()
    start_date: date = data["start_date"]
    end_date: date = data["end_date"]
    is_half_day = bool(data.get("is_half_day", False))

    emp = session.get(Employee, employee_id)
    if not emp:
        raise NotFoundError(f"Employee '{employee_id}' not found")

    leave_type = session.get(LeaveType, leave_type_code)
    if not leave_type:
        raise NotFoundError(f"Leave type '{leave_type_code}' not found")

    days = count_working_days(session, start_date, end_date, is_half_day=is_half_day)
    if days <= Decimal("0.00"):
        raise ValidationError("Leave request spans 0 working days (weekends and holidays are excluded)")

    balance = get_or_create_leave_balance(session, employee_id)
    available = _available_balance_for_type(balance, leave_type)

    applied_on = data.get("applied_on") or date.today()
    request_id = data.get("leave_request_id") or f"LR-{uuid.uuid4().hex[:6].upper()}"

    if available is not None and days > available:
        if auto_reject_insufficient:
            rejected_req = LeaveRequest(
                leave_request_id=request_id,
                employee_id=employee_id,
                leave_type_code=leave_type_code,
                start_date=start_date,
                end_date=end_date,
                days=days,
                reason=data.get("reason"),
                status="Rejected",
                applied_on=applied_on,
                approver_id=emp.manager_id,
                decided_on=applied_on,
            )
            session.add(rejected_req)
            session.commit()
            session.refresh(rejected_req)
            return rejected_req

        raise AppException(
            f"Insufficient {leave_type_code} leave balance: available {available} days, requested {days} days",
            error_code="INSUFFICIENT_BALANCE",
            status_code=400,
        )

    leave_req = LeaveRequest(
        leave_request_id=request_id,
        employee_id=employee_id,
        leave_type_code=leave_type_code,
        start_date=start_date,
        end_date=end_date,
        days=days,
        reason=data.get("reason"),
        status="Pending",
        applied_on=applied_on,
        approver_id=None,
        decided_on=None,
    )
    balance.pending_days = (Decimal(str(balance.pending_days)) + days).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    session.add(leave_req)
    session.commit()
    session.refresh(leave_req)
    return leave_req


def approve_leave(
    session: Session,
    leave_request_id: str,
    approver_id: str | None = None,
    decided_on: date | None = None,
    auto_reject_insufficient: bool = False,
) -> LeaveRequest:
    """Approve a pending leave request and deduct working days from the employee's balance.
    If the balance is no longer sufficient at approval time, rejects the request.
    """
    leave_req = session.get(LeaveRequest, leave_request_id)
    if not leave_req:
        raise NotFoundError(f"Leave request '{leave_request_id}' not found")

    if leave_req.status != "Pending":
        raise ConflictError(
            f"Cannot approve leave request '{leave_request_id}' with status '{leave_req.status}'"
        )

    if approver_id:
        approver = session.get(Employee, approver_id)
        if not approver:
            raise NotFoundError(f"Approver employee '{approver_id}' not found")

    balance = get_or_create_leave_balance(session, leave_req.employee_id)
    leave_type = session.get(LeaveType, leave_req.leave_type_code)
    available = _available_balance_for_type(balance, leave_type) if leave_type else None
    days = Decimal(str(leave_req.days)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if available is not None and days > available:
        balance.pending_days = max(
            Decimal("0.00"),
            (Decimal(str(balance.pending_days)) - days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        )
        if auto_reject_insufficient:
            leave_req.status = "Rejected"
            leave_req.approver_id = approver_id
            leave_req.decided_on = decided_on or date.today()
            session.commit()
            session.refresh(leave_req)
            return leave_req

        session.commit()
        raise AppException(
            f"Insufficient {leave_req.leave_type_code} leave balance: available {available} days, requested {days} days",
            error_code="INSUFFICIENT_BALANCE",
            status_code=400,
        )

    code = leave_req.leave_type_code.upper()
    if code == "CL":
        balance.cl_used = (Decimal(str(balance.cl_used)) + days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        balance.cl_balance = (Decimal(str(balance.cl_balance)) - days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif code == "SL":
        balance.sl_used = (Decimal(str(balance.sl_used)) + days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        balance.sl_balance = (Decimal(str(balance.sl_balance)) - days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif code == "EL":
        balance.el_used_fy = (Decimal(str(balance.el_used_fy)) + days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        balance.el_balance = (Decimal(str(balance.el_balance)) - days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    balance.pending_days = max(
        Decimal("0.00"),
        (Decimal(str(balance.pending_days)) - days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    )

    leave_req.status = "Approved"
    leave_req.approver_id = approver_id
    leave_req.decided_on = decided_on or date.today()

    session.commit()
    session.refresh(leave_req)
    return leave_req


def reject_leave(
    session: Session,
    leave_request_id: str,
    approver_id: str | None = None,
    decided_on: date | None = None,
) -> LeaveRequest:
    """Reject a pending leave request without deducting from the employee's leave balance."""
    leave_req = session.get(LeaveRequest, leave_request_id)
    if not leave_req:
        raise NotFoundError(f"Leave request '{leave_request_id}' not found")

    if leave_req.status != "Pending":
        raise ConflictError(
            f"Cannot reject leave request '{leave_request_id}' with status '{leave_req.status}'"
        )

    if approver_id:
        approver = session.get(Employee, approver_id)
        if not approver:
            raise NotFoundError(f"Approver employee '{approver_id}' not found")

    balance = get_or_create_leave_balance(session, leave_req.employee_id)
    days = Decimal(str(leave_req.days)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    balance.pending_days = max(
        Decimal("0.00"),
        (Decimal(str(balance.pending_days)) - days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    )

    leave_req.status = "Rejected"
    leave_req.approver_id = approver_id
    leave_req.decided_on = decided_on or date.today()

    session.commit()
    session.refresh(leave_req)
    return leave_req


def list_leave_requests(
    session: Session,
    employee_id: str | None = None,
    status: str | None = None,
) -> list[LeaveRequest]:
    """List leave requests with optional employee_id and status filters."""
    stmt = select(LeaveRequest)
    if employee_id:
        stmt = stmt.where(LeaveRequest.employee_id == employee_id)
    if status:
        stmt = stmt.where(LeaveRequest.status == status)
    stmt = stmt.order_by(LeaveRequest.start_date.desc(), LeaveRequest.leave_request_id)
    return list(session.scalars(stmt).all())
