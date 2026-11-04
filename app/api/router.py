"""Collects all route modules."""

from fastapi import APIRouter

from app.api.routes import (
    attendance,
    auth,
    departments,
    employees,
    expense,
    health,
    invoice,
    leave,
    ledger,
    payroll,
    payslip,
    reports,
    tax,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(departments.router)
api_router.include_router(employees.router)
api_router.include_router(attendance.router)
api_router.include_router(leave.router)
api_router.include_router(payroll.router)
api_router.include_router(payslip.router)
api_router.include_router(ledger.router)
api_router.include_router(invoice.router)
api_router.include_router(expense.router)
api_router.include_router(tax.router)
api_router.include_router(reports.router)
