"""Vendor and Expense bill models (LF-11)."""

from datetime import date
from decimal import Decimal
from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Vendor(Base):
    __tablename__ = "vendors"

    vendor_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    vendor_name: Mapped[str] = mapped_column(String(128))
    primary_expense_account: Mapped[int] = mapped_column(Integer)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, server_default="30")
    city: Mapped[str] = mapped_column(String(64))
    gst_registration: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[str] = mapped_column(String(4), default="Y", server_default="Y")

    def __repr__(self) -> str:
        return f"<Vendor {self.vendor_id} {self.vendor_name} acct={self.primary_expense_account}>"


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expenses_vendor_id", "vendor_id"),
        Index("ix_expenses_status", "status"),
        Index("ix_expenses_expense_date", "expense_date"),
        Index("ix_expenses_department_id", "department_id"),
    )

    expense_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    expense_date: Mapped[date] = mapped_column(Date)
    category_account: Mapped[int] = mapped_column(Integer)
    vendor_id: Mapped[str] = mapped_column(String(16), ForeignKey("vendors.vendor_id"))
    bill_reference: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(String(255))
    department_id: Mapped[str] = mapped_column(String(16), ForeignKey("departments.department_id"))
    amount_excl_gst: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    gst_rate_percent: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), default=Decimal("18.00"), server_default="18"
    )
    gst_amount: Mapped[Decimal] = mapped_column(
        Numeric(16, 2), default=Decimal("0.00"), server_default="0"
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    due_date: Mapped[date] = mapped_column(Date)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="SUBMITTED", server_default="SUBMITTED")
    payment_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    submitted_by: Mapped[str] = mapped_column(String(32))
    approved_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ledger_entry_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payment_ledger_entry_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    def __repr__(self) -> str:
        return f"<Expense {self.expense_id} vendor={self.vendor_id} status={self.status} total={self.total_amount}>"
