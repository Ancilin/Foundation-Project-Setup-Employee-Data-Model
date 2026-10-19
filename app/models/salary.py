"""Salary models: pay components, effective-dated structures, and salary revisions (LF-05)."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class SalaryComponent(Base):
    """Component definition (BASIC, HRA, SPECIAL_ALLOWANCE, PF, etc.)."""
    __tablename__ = "salary_components"

    component_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    component_name: Mapped[str] = mapped_column(String(100))
    component_type: Mapped[str] = mapped_column(String(32))  # EARNING or DEDUCTION
    taxable: Mapped[str] = mapped_column(String(1), default="Y")  # Y or N
    calculation_rule: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_fixed: Mapped[str] = mapped_column(String(1), default="Y")  # Y or N

    def __repr__(self) -> str:
        return f"<SalaryComponent {self.component_id}: {self.component_name} ({self.component_type})>"


class SalaryRevision(TimestampMixin, Base):
    """Record of every salary increase, promotion, or adjustment."""
    __tablename__ = "salary_revisions"
    __table_args__ = (
        Index("ix_revisions_employee_id", "employee_id"),
        Index("ix_revisions_effective_from", "effective_from"),
    )

    revision_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"))
    effective_from: Mapped[date] = mapped_column(Date)
    revision_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    previous_annual_fixed: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    new_annual_fixed: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    pct_change: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    role_id_after: Mapped[str | None] = mapped_column(String(16), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(10), nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="salary_revisions")

    def __repr__(self) -> str:
        return f"<SalaryRevision {self.revision_id} emp={self.employee_id} new_ctc={self.new_annual_fixed} change={self.pct_change}%>"


class SalaryStructure(TimestampMixin, Base):
    """Effective-dated breakdown of monthly pay components for an employee."""
    __tablename__ = "salary_structures"
    __table_args__ = (
        Index("ix_structures_employee_id", "employee_id"),
        Index("ix_structures_effective_from", "effective_from"),
        Index("ix_structures_effective_to", "effective_to"),
    )

    structure_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"))
    component_id: Mapped[str] = mapped_column(ForeignKey("salary_components.component_id"))
    component_name: Mapped[str] = mapped_column(String(100))
    component_type: Mapped[str] = mapped_column(String(32))
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    revision_id: Mapped[str | None] = mapped_column(String(32), nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="salary_structures")
    component: Mapped["SalaryComponent"] = relationship()

    def __repr__(self) -> str:
        return f"<SalaryStructure {self.structure_id} emp={self.employee_id} {self.component_id}={self.monthly_amount}>"


class Salary(TimestampMixin, Base):
    """Aggregated annual salary for baseline employee queries and backward compatibility."""
    __tablename__ = "salaries"
    __table_args__ = (
        Index("ix_salaries_employee_id", "employee_id"),
        Index("ix_salaries_effective_from", "effective_from"),
    )

    salary_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"))
    monthly_gross: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    basic: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    hra: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    special_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    annual_ctc: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="salaries")

    def __repr__(self) -> str:
        return f"<Salary {self.salary_id} emp={self.employee_id} ctc={self.annual_ctc}>"
