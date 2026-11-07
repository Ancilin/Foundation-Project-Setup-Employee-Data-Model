"""Attendance model linked to employees (LF-06)."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee

ATTENDANCE_STATUSES = (
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
)


class Attendance(TimestampMixin, Base):
    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_employee_date"),
        CheckConstraint(
            f"status IN {ATTENDANCE_STATUSES}",
            name="attendance_status_valid",
        ),
        Index("ix_attendance_employee_date", "employee_id", "attendance_date"),
        Index("ix_attendance_date", "attendance_date"),
    )

    attendance_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(10), ForeignKey("employees.employee_id"))
    attendance_date: Mapped[date] = mapped_column(Date)
    weekday: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20))
    leave_type_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    check_in: Mapped[str | None] = mapped_column(String(10), nullable=True)
    check_out: Mapped[str | None] = mapped_column(String(10), nullable=True)
    hours_worked: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    overtime_hours: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal("0.00"), server_default="0")
    late_flag: Mapped[str] = mapped_column(String(1), default="N", server_default="N")
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    data_quality_flag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    department_id: Mapped[str | None] = mapped_column(String(10), nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="attendance_records")

    def __repr__(self) -> str:
        return f"<Attendance {self.attendance_id} emp={self.employee_id} date={self.attendance_date} status={self.status}>"
