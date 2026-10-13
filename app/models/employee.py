"""Employee: the central record. Includes the self-referencing manager hierarchy."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.role import Role

GENDERS = ("Male", "Female", "Other")
EMPLOYMENT_STATUSES = ("Active", "Resigned", "Terminated", "Contract Ended")
EMPLOYMENT_TYPES = ("Permanent", "Fixed-Term Contract")
WORK_MODES = ("Onsite", "Hybrid", "Remote")


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        # Allowed values are enforced by the database (CHECK), not only by the app.
        CheckConstraint(_in_list("gender", GENDERS), name="gender_valid"),
        CheckConstraint(_in_list("employment_status", EMPLOYMENT_STATUSES), name="employment_status_valid"),
        CheckConstraint(_in_list("employment_type", EMPLOYMENT_TYPES), name="employment_type_valid"),
        CheckConstraint(_in_list("work_mode", WORK_MODES), name="work_mode_valid"),
        CheckConstraint("exit_date IS NULL OR exit_date >= hire_date", name="exit_after_hire"),
        CheckConstraint("hire_date > date_of_birth", name="hire_after_birth"),
        # Nobody manages themselves (longer cycles are rejected by the service layer).
        CheckConstraint("manager_id IS NULL OR manager_id <> employee_id", name="not_own_manager"),
        # Indexes on the columns people search/filter by.
        Index("ix_employees_name", "last_name", "first_name"),
        Index("ix_employees_department_id", "department_id"),
        Index("ix_employees_role_id", "role_id"),
        Index("ix_employees_manager_id", "manager_id"),
        Index("ix_employees_employment_status", "employment_status"),
    )

    # Natural key from the dataset (EMP-0001 ...), identical in every table/workbook.
    employee_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    work_email: Mapped[str] = mapped_column(String(255), unique=True)
    gender: Mapped[str] = mapped_column(String(10))
    date_of_birth: Mapped[date] = mapped_column(Date)
    hire_date: Mapped[date] = mapped_column(Date)
    exit_date: Mapped[date | None] = mapped_column(Date)
    employment_status: Mapped[str] = mapped_column(String(20), default="Active", server_default="Active")
    employment_type: Mapped[str] = mapped_column(String(20), default="Permanent", server_default="Permanent")
    work_location: Mapped[str] = mapped_column(String(80))
    work_mode: Mapped[str] = mapped_column(String(10))

    department_id: Mapped[str] = mapped_column(ForeignKey("departments.department_id"))
    # One CURRENT role per employee (see README for the reasoning).
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.role_id"))
    # Self-reference: NULL only for the top of the hierarchy (the CEO).
    manager_id: Mapped[str | None] = mapped_column(ForeignKey("employees.employee_id"))

    department: Mapped["Department"] = relationship(back_populates="employees")
    role: Mapped["Role"] = relationship(back_populates="employees")
    manager: Mapped["Employee | None"] = relationship(
        back_populates="direct_reports", remote_side=[employee_id]
    )
    direct_reports: Mapped[list["Employee"]] = relationship(back_populates="manager")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Employee {self.employee_id} {self.full_name!r}>"
