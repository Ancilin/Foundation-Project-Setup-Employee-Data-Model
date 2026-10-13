"""Salary model linked to employees."""

from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee


class Salary(TimestampMixin, Base):
    __tablename__ = "salaries"
    __table_args__ = (
        Index("ix_salaries_employee_id", "employee_id"),
        Index("ix_salaries_effective_from", "effective_from"),
    )

    salary_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"))
    monthly_gross: Mapped[float] = mapped_column(Numeric(12, 2))
    basic: Mapped[float] = mapped_column(Numeric(12, 2))
    hra: Mapped[float] = mapped_column(Numeric(12, 2))
    special_allowance: Mapped[float] = mapped_column(Numeric(12, 2))
    annual_ctc: Mapped[float] = mapped_column(Numeric(14, 2))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="salaries")

    def __repr__(self) -> str:
        return f"<Salary {self.salary_id} emp={self.employee_id} ctc={self.annual_ctc}>"
