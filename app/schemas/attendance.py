"""Pydantic schemas for Attendance recording, listing, and monthly summary (LF-06)."""

from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

AttendanceStatusType = Literal[
    "PRESENT",
    "ABSENT",
    "WFH",
    "HALF_DAY",
    "ON_LEAVE",
    "PAID_LEAVE",
    "ABSENT_LOP",
    "HALF_DAY_UNPAID",
    "UNPAID_LEAVE",
    "HALF_DAY_PAID",
]


class AttendanceCreate(BaseModel):
    attendance_id: str | None = Field(None, max_length=32)
    employee_id: str = Field(..., min_length=1, max_length=10)
    attendance_date: date
    status: AttendanceStatusType
    leave_type_code: str | None = Field(None, max_length=10)
    check_in: str | None = Field(None, max_length=10)
    check_out: str | None = Field(None, max_length=10)
    hours_worked: Decimal | None = None
    overtime_hours: Decimal = Decimal("0.00")
    late_flag: Literal["Y", "N"] | None = None
    source: str | None = Field("Web Check-in", max_length=32)
    data_quality_flag: str | None = Field(None, max_length=32)
    department_id: str | None = Field(None, max_length=10)


class AttendanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    attendance_id: str
    employee_id: str
    attendance_date: date
    weekday: str
    status: str
    leave_type_code: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    hours_worked: Decimal | None = None
    overtime_hours: Decimal
    late_flag: str
    source: str | None = None
    data_quality_flag: str | None = None
    department_id: str | None = None


class MonthlySummaryRead(BaseModel):
    employee_id: str
    month: str
    total_working_days: int
    days_present: int
    days_wfh: int
    days_absent: int
    absent_lop_days: int
    unpaid_leave_days: int
    paid_leave_days: int
    half_days: int
    lop_days: Decimal
    late_days: int
    overtime_hours: Decimal
    total_hours_worked: Decimal
    missing_checkout_count: int
