"""Database models (SQLAlchemy). Importing this package registers every table on Base.metadata."""

from app.models.assignment import EmployeeAssignment
from app.models.attendance import Attendance
from app.models.base import Base
from app.models.department import Department
from app.models.employee import Employee
from app.models.invoice import Client, Invoice, InvoiceItem, InvoicePayment
from app.models.leave import Holiday, LeaveBalance, LeaveRequest, LeaveType
from app.models.ledger import ChartOfAccount, JournalEntry, JournalLine
from app.models.payroll import (
    PayrollItem,
    PayrollRun,
    StatutoryRate,
    TaxParameter,
    TaxSlab,
)
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
    "ChartOfAccount",
    "Client",
    "Department",
    "Employee",
    "EmployeeAssignment",
    "Holiday",
    "Invoice",
    "InvoiceItem",
    "InvoicePayment",
    "JournalEntry",
    "JournalLine",
    "LeaveBalance",
    "LeaveRequest",
    "LeaveType",
    "PayrollItem",
    "PayrollRun",
    "Role",
    "Salary",
    "SalaryComponent",
    "SalaryRevision",
    "SalaryStructure",
    "StatutoryRate",
    "TaxParameter",
    "TaxSlab",
]
