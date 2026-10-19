"""Database models (SQLAlchemy). Importing this package registers every table on Base.metadata."""

from app.models.assignment import EmployeeAssignment
from app.models.attendance import Attendance
from app.models.base import Base
from app.models.department import Department
from app.models.employee import Employee
from app.models.role import Role
from app.models.salary import (
    Salary,
    SalaryComponent,
    SalaryRevision,
    SalaryStructure,
)

__all__ = [
    "Attendance",
    "Base",
    "Department",
    "Employee",
    "EmployeeAssignment",
    "Role",
    "Salary",
    "SalaryComponent",
    "SalaryRevision",
    "SalaryStructure",
]
