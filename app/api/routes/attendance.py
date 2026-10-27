"""Attendance HTTP routes: record, list by employee/month, and monthly summary (LF-06)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.attendance import AttendanceCreate, AttendanceRead, MonthlySummaryRead
from app.services import attendance_service

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("", response_model=AttendanceRead, status_code=status.HTTP_201_CREATED)
def create_attendance_record(
    payload: AttendanceCreate,
    db: Session = Depends(get_db),
):
    """Record a daily attendance entry for an employee."""
    return attendance_service.record_attendance(db, payload)


@router.get("/{employee_id}", response_model=list[AttendanceRead])
def get_employee_attendance(
    employee_id: str,
    month: str | None = Query(None, description="Optional month filter in YYYY-MM format"),
    db: Session = Depends(get_db),
):
    """List attendance records for an employee, optionally filtered by month (YYYY-MM)."""
    return attendance_service.list_employee_attendance(db, employee_id, month=month)


@router.get("/{employee_id}/summary", response_model=MonthlySummaryRead)
def get_employee_monthly_summary_query(
    employee_id: str,
    month: str = Query(..., description="Target month in YYYY-MM format"),
    db: Session = Depends(get_db),
):
    """Compute monthly attendance summary for an employee and month (via query param)."""
    return attendance_service.monthly_summary(db, employee_id, month)


@router.get("/{employee_id}/summary/{month}", response_model=MonthlySummaryRead)
def get_employee_monthly_summary_path(
    employee_id: str,
    month: str,
    db: Session = Depends(get_db),
):
    """Compute monthly attendance summary for an employee and month (via path param)."""
    return attendance_service.monthly_summary(db, employee_id, month)
