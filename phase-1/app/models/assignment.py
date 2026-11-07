"""EmployeeAssignment: tracking role, department, and manager changes over time."""

from datetime import date
from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class EmployeeAssignment(TimestampMixin, Base):
    __tablename__ = "employee_assignments"
    __table_args__ = (
        Index("ix_assignments_employee_id", "employee_id"),
        Index("ix_assignments_effective_from", "effective_from"),
        Index("ix_assignments_department_id", "department_id"),
    )

    assignment_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.employee_id"))
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.department_id"))
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.role_id"))
    job_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    manager_id: Mapped[str | None] = mapped_column(String(10), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="assignments")

    def __repr__(self) -> str:
        return f"<EmployeeAssignment {self.assignment_id} emp={self.employee_id} dept={self.department_id} from={self.effective_from}>"
