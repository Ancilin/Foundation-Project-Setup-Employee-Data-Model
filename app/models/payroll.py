"""Payroll, StatutoryRate, TaxSlab, and TaxParameter models (LF-07)."""

from datetime import date
from decimal import Decimal
from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class StatutoryRate(Base):
    __tablename__ = "statutory_rates"

    parameter: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    unit: Mapped[str] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_from: Mapped[date] = mapped_column(Date)

    def __repr__(self) -> str:
        return f"<StatutoryRate {self.parameter}={self.value}>"


class TaxParameter(Base):
    __tablename__ = "tax_parameters"

    parameter: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<TaxParameter {self.parameter}={self.value}>"


class TaxSlab(Base):
    __tablename__ = "tax_slabs"

    slab_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    regime: Mapped[str] = mapped_column(String(16), default="NEW", server_default="NEW")
    financial_year: Mapped[str] = mapped_column(String(16))
    income_from: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    income_to: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    effective_from: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<TaxSlab {self.slab_id} {self.financial_year} {self.income_from}-{self.income_to} @ {self.rate_percent}%>"


class PayrollRun(TimestampMixin, Base):
    __tablename__ = "payroll_runs"

    run_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    pay_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    employees_paid: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_gross: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0.00"), server_default="0")
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0.00"), server_default="0")
    total_net: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0.00"), server_default="0")
    total_employer_contributions: Mapped[Decimal] = mapped_column(
        Numeric(16, 2), default=Decimal("0.00"), server_default="0"
    )
    total_employer_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0.00"), server_default="0")
    status: Mapped[str] = mapped_column(String(32), default="PAID", server_default="PAID")
    run_by: Mapped[str | None] = mapped_column(String(16), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(16), nullable=True)
    approved_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    journal_entry_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    calculation_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    def __repr__(self) -> str:
        return f"<PayrollRun {self.run_id} status={self.status} net={self.total_net}>"


class PayrollItem(TimestampMixin, Base):
    __tablename__ = "payroll_items"
    __table_args__ = (
        UniqueConstraint("run_id", "employee_id", name="uq_payroll_items_run_employee"),
        Index("ix_payroll_items_run_id", "run_id"),
        Index("ix_payroll_items_employee_id", "employee_id"),
    )

    payroll_item_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(20), ForeignKey("payroll_runs.run_id"))
    employee_id: Mapped[str] = mapped_column(String(10), ForeignKey("employees.employee_id"))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    department_id: Mapped[str] = mapped_column(String(10))
    role_id: Mapped[str] = mapped_column(String(10))
    calendar_days: Mapped[int] = mapped_column(Integer)
    days_employed: Mapped[int] = mapped_column(Integer)
    lop_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), server_default="0")
    payable_days: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    monthly_fixed_gross: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    basic: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    hra: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    conveyance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    medical: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    special_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    earned_fixed_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    overtime_hours_paid: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("0.00"), server_default="0")
    overtime_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), server_default="0")
    variable_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), server_default="0")
    variable_pay_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gross_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    pf_employee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), server_default="0")
    esi_employee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), server_default="0")
    professional_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), server_default="0")
    tds: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), server_default="0")
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), server_default="0")
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    net_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    pf_employer: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), server_default="0")
    esi_employer: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), server_default="0")
    employer_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    calculation_note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<PayrollItem {self.payroll_item_id} run={self.run_id} emp={self.employee_id} net={self.net_pay}>"
