"""Holiday, LeaveType, LeaveBalance, and LeaveRequest models (LF-06)."""

from datetime import date
from decimal import Decimal
from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

LEAVE_REQUEST_STATUSES = ("Pending", "Approved", "Rejected", "Cancelled")


class Holiday(Base):
    __tablename__ = "holidays"

    holiday_date: Mapped[date] = mapped_column(Date, primary_key=True)
    holiday_name: Mapped[str] = mapped_column(String(150))
    holiday_type: Mapped[str] = mapped_column(String(32))
    weekday: Mapped[str] = mapped_column(String(16))
    falls_on_weekend: Mapped[str] = mapped_column(String(1), default="N", server_default="N")
    calendar_note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<Holiday {self.holiday_date} {self.holiday_name}>"


class LeaveType(Base):
    __tablename__ = "leave_types"

    leave_type_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    leave_type_name: Mapped[str] = mapped_column(String(100))
    pay_type: Mapped[str] = mapped_column(String(20))
    annual_quota_days: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    prorated_for_joiners: Mapped[str] = mapped_column(String(1), default="N", server_default="N")
    carry_forward_allowed: Mapped[str] = mapped_column(String(1), default="N", server_default="N")
    max_carry_forward_days: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    policy_note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<LeaveType {self.leave_type_code} ({self.pay_type})>"


class LeaveBalance(TimestampMixin, Base):
    __tablename__ = "leave_balances"

    employee_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("employees.employee_id"), primary_key=True
    )
    as_of_date: Mapped[date] = mapped_column(Date)
    financial_year: Mapped[str] = mapped_column(String(16))
    cl_entitlement: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("12.00"), server_default="12")
    cl_used: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), server_default="0")
    cl_balance: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("12.00"), server_default="12")
    sl_entitlement: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("12.00"), server_default="12")
    sl_used: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), server_default="0")
    sl_balance: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("12.00"), server_default="12")
    el_used_fy: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), server_default="0")
    el_balance: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), server_default="0")
    pending_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), server_default="0")

    def __repr__(self) -> str:
        return f"<LeaveBalance emp={self.employee_id} cl={self.cl_balance} sl={self.sl_balance} el={self.el_balance}>"


class LeaveRequest(TimestampMixin, Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        CheckConstraint(
            f"status IN {LEAVE_REQUEST_STATUSES}",
            name="leave_request_status_valid",
        ),
        Index("ix_leave_requests_employee_id", "employee_id"),
        Index("ix_leave_requests_start_date", "start_date"),
    )

    leave_request_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(10), ForeignKey("employees.employee_id"))
    leave_type_code: Mapped[str] = mapped_column(String(10), ForeignKey("leave_types.leave_type_code"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending", server_default="Pending")
    applied_on: Mapped[date] = mapped_column(Date)
    approver_id: Mapped[str | None] = mapped_column(
        String(10), ForeignKey("employees.employee_id"), nullable=True
    )
    decided_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    def __repr__(self) -> str:
        return f"<LeaveRequest {self.leave_request_id} emp={self.employee_id} type={self.leave_type_code} days={self.days} status={self.status}>"
