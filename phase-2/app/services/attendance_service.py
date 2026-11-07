"""Attendance service: recording, listing, working-day rules, and monthly summary (LF-06)."""

import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, ConflictError, NotFoundError, ValidationError
from app.db.session import get_engine
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.leave import Holiday
from app.schemas.attendance import AttendanceCreate


class MonthlySummaryResult(dict):
    """Dictionary result for monthly_summary that also supports attribute access and common aliases."""

    def __getattr__(self, name: str) -> Any:
        if name in self:
            return self[name]
        aliases = {
            "present": "days_present",
            "wfh": "days_wfh",
            "work_from_home": "days_wfh",
            "absent": "days_absent",
            "late": "late_days",
            "overtime": "overtime_hours",
        }
        if name in aliases and aliases[name] in self:
            return self[aliases[name]]
        raise AttributeError(f"'MonthlySummaryResult' object has no attribute '{name}'")

    def __getitem__(self, key: str) -> Any:
        if key in self.keys():
            return super().__getitem__(key)
        aliases = {
            "present": "days_present",
            "wfh": "days_wfh",
            "work_from_home": "days_wfh",
            "absent": "days_absent",
            "late": "late_days",
            "overtime": "overtime_hours",
        }
        if key in aliases:
            return super().__getitem__(aliases[key])
        raise KeyError(key)


def get_holiday_dates(
    session: Session,
    start_date: date | None = None,
    end_date: date | None = None,
) -> set[date]:
    """Return the set of company holiday dates within the optional date range."""
    stmt = select(Holiday.holiday_date)
    if start_date is not None:
        stmt = stmt.where(Holiday.holiday_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(Holiday.holiday_date <= end_date)
    return set(session.scalars(stmt).all())


def is_working_day(
    session: Session,
    target_date: date,
    holiday_dates: set[date] | None = None,
) -> bool:
    """Return True if target_date is Monday-Friday and not a company holiday."""
    if target_date.weekday() >= 5:
        return False
    if holiday_dates is None:
        holiday_dates = get_holiday_dates(session, target_date, target_date)
    return target_date not in holiday_dates


def count_working_days(
    session: Session,
    start_date: date,
    end_date: date,
    is_half_day: bool = False,
) -> Decimal:
    """Count working days between start_date and end_date inclusive, skipping weekends and holidays."""
    if end_date < start_date:
        raise ValidationError("end_date cannot be earlier than start_date")

    if is_half_day and start_date != end_date:
        raise ValidationError("Half-day leave must have the same start_date and end_date")

    holiday_dates = get_holiday_dates(session, start_date, end_date)
    working_days = 0
    curr = start_date
    while curr <= end_date:
        if curr.weekday() < 5 and curr not in holiday_dates:
            working_days += 1
        curr += timedelta(days=1)

    if is_half_day:
        return Decimal("0.50") if working_days == 1 else Decimal("0.00")

    return Decimal(working_days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _parse_month_bounds(month: str) -> tuple[date, date]:
    """Parse 'YYYY-MM' into (first_day, last_day) of the month."""
    try:
        parts = month.strip().split("-")
        if len(parts) != 2:
            raise ValueError
        year = int(parts[0])
        mon = int(parts[1])
        _, last_day_num = calendar.monthrange(year, mon)
        return date(year, mon, 1), date(year, mon, last_day_num)
    except Exception as exc:
        raise ValidationError(f"Invalid month format '{month}'. Expected 'YYYY-MM'.") from exc


def record_attendance(
    session: Session,
    payload: AttendanceCreate | dict[str, Any],
) -> Attendance:
    """Record a single daily attendance entry, applying MISSING_CHECKOUT and late rules."""
    data = payload.model_dump() if isinstance(payload, AttendanceCreate) else dict(payload)
    employee_id = data["employee_id"]
    att_date: date = data["attendance_date"]

    emp = session.get(Employee, employee_id)
    if not emp:
        raise NotFoundError(f"Employee '{employee_id}' not found")

    existing = session.scalar(
        select(Attendance).where(
            Attendance.employee_id == employee_id,
            Attendance.attendance_date == att_date,
        )
    )
    if existing:
        raise ConflictError(f"Attendance already recorded for {employee_id} on {att_date}")

    status = data["status"]
    check_in = data.get("check_in")
    check_out = data.get("check_out")
    data_quality_flag = data.get("data_quality_flag")
    hours_worked = data.get("hours_worked")
    overtime_hours = Decimal(str(data.get("overtime_hours") or "0.00")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # MISSING_CHECKOUT rule:
    # If check_in exists without check_out on a working status or explicitly flagged MISSING_CHECKOUT:
    # Honor the attendance status, set hours_worked to None, and disallow overtime (0.00).
    if data_quality_flag == "MISSING_CHECKOUT" or (
        status in ("PRESENT", "WFH", "HALF_DAY_UNPAID", "HALF_DAY", "HALF_DAY_PAID")
        and check_in is not None
        and check_out is None
    ):
        data_quality_flag = "MISSING_CHECKOUT"
        hours_worked = None
        overtime_hours = Decimal("0.00")
    elif hours_worked is not None:
        hours_worked = Decimal(str(hours_worked)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    late_flag = data.get("late_flag")
    if late_flag is None:
        if check_in and check_in > "09:45":
            late_flag = "Y"
        else:
            late_flag = "N"

    att_id = data.get("attendance_id") or f"ATT-{employee_id}-{att_date.strftime('%Y%m%d')}"
    weekday_str = att_date.strftime("%a")
    dept_id = data.get("department_id") or emp.department_id

    record = Attendance(
        attendance_id=att_id,
        employee_id=employee_id,
        attendance_date=att_date,
        weekday=weekday_str,
        status=status,
        leave_type_code=data.get("leave_type_code"),
        check_in=check_in,
        check_out=check_out,
        hours_worked=hours_worked,
        overtime_hours=overtime_hours,
        late_flag=late_flag,
        source=data.get("source") or "Web Check-in",
        data_quality_flag=data_quality_flag,
        department_id=dept_id,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def list_employee_attendance(
    session: Session,
    employee_id: str,
    month: str | None = None,
) -> list[Attendance]:
    """List attendance rows for an employee, optionally filtered by month ('YYYY-MM')."""
    emp = session.get(Employee, employee_id)
    if not emp:
        raise NotFoundError(f"Employee '{employee_id}' not found")

    stmt = select(Attendance).where(Attendance.employee_id == employee_id)
    if month:
        start_d, end_d = _parse_month_bounds(month)
        stmt = stmt.where(
            Attendance.attendance_date >= start_d,
            Attendance.attendance_date <= end_d,
        )
    stmt = stmt.order_by(Attendance.attendance_date)
    return list(session.scalars(stmt).all())


def _compute_monthly_summary(
    session: Session,
    employee_id: str,
    month: str,
) -> MonthlySummaryResult:
    emp = session.get(Employee, employee_id)
    if not emp:
        raise NotFoundError(f"Employee '{employee_id}' not found")

    start_d, end_d = _parse_month_bounds(month)
    rows = list(
        session.scalars(
            select(Attendance)
            .where(
                Attendance.employee_id == employee_id,
                Attendance.attendance_date >= start_d,
                Attendance.attendance_date <= end_d,
            )
            .order_by(Attendance.attendance_date)
        ).all()
    )

    days_present = 0
    days_wfh = 0
    absent_lop_days = 0
    unpaid_leave_days = 0
    paid_leave_days = 0
    half_days = 0
    half_day_unpaid_count = 0
    late_days = 0
    overtime_hours = Decimal("0.00")
    total_hours_worked = Decimal("0.00")
    missing_checkout_count = 0

    for r in rows:
        st = (r.status or "").upper()
        is_mc = r.data_quality_flag == "MISSING_CHECKOUT"

        if is_mc:
            missing_checkout_count += 1

        # Status classification (MISSING_CHECKOUT honors the recorded check-in status)
        if st == "PRESENT":
            days_present += 1
        elif st == "WFH":
            days_wfh += 1
        elif st in ("ABSENT_LOP", "ABSENT"):
            absent_lop_days += 1
        elif st == "UNPAID_LEAVE":
            unpaid_leave_days += 1
        elif st in ("PAID_LEAVE", "ON_LEAVE"):
            paid_leave_days += 1
        elif st in ("HALF_DAY_UNPAID", "HALF_DAY"):
            half_days += 1
            half_day_unpaid_count += 1
        elif st == "HALF_DAY_PAID":
            half_days += 1

        if (r.late_flag or "N").upper() == "Y":
            late_days += 1

        # MISSING_CHECKOUT rule: missing check-out cannot claim overtime; null hours_worked is safely 0.00
        if not is_mc:
            if r.overtime_hours is not None:
                overtime_hours += Decimal(str(r.overtime_hours))
            if r.hours_worked is not None:
                total_hours_worked += Decimal(str(r.hours_worked))

    days_absent = absent_lop_days + unpaid_leave_days
    lop_days = (
        Decimal(absent_lop_days + unpaid_leave_days)
        + (Decimal("0.50") * Decimal(half_day_unpaid_count))
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    overtime_hours = overtime_hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_hours_worked = total_hours_worked.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    total_working_days = len(rows) if rows else int(count_working_days(session, start_d, end_d))

    return MonthlySummaryResult(
        employee_id=employee_id,
        month=month,
        total_working_days=total_working_days,
        days_present=days_present,
        days_wfh=days_wfh,
        days_absent=days_absent,
        absent_lop_days=absent_lop_days,
        unpaid_leave_days=unpaid_leave_days,
        paid_leave_days=paid_leave_days,
        half_days=half_days,
        lop_days=lop_days,
        late_days=late_days,
        overtime_hours=overtime_hours,
        total_hours_worked=total_hours_worked,
        missing_checkout_count=missing_checkout_count,
    )


def monthly_summary(
    session_or_employee: Session | Employee | str,
    employee_or_month: Employee | str,
    month: str | None = None,
) -> MonthlySummaryResult:
    """Compute the monthly attendance summary for an employee and month ('YYYY-MM').

    Supports calling conventions:
      - monthly_summary(session, employee_id_or_obj, '2025-05')
      - monthly_summary(employee_id_or_obj, '2025-05')
    """
    if isinstance(session_or_employee, Session):
        session = session_or_employee
        emp_id = (
            employee_or_month.employee_id
            if isinstance(employee_or_month, Employee)
            else str(employee_or_month)
        )
        if not month:
            raise ValidationError("month parameter ('YYYY-MM') is required")
        return _compute_monthly_summary(session, emp_id, month)

    emp_id = (
        session_or_employee.employee_id
        if isinstance(session_or_employee, Employee)
        else str(session_or_employee)
    )
    target_month = str(employee_or_month)
    with Session(get_engine()) as session:
        return _compute_monthly_summary(session, emp_id, target_month)
