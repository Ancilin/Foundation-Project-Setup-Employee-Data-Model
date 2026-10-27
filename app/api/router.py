"""Collects all route modules."""

from fastapi import APIRouter

from app.api.routes import attendance, departments, employees, health, invoice, leave, ledger, payroll, payslip

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(departments.router)
api_router.include_router(employees.router)
api_router.include_router(attendance.router)
api_router.include_router(leave.router)
api_router.include_router(payroll.router)
api_router.include_router(payslip.router)
api_router.include_router(ledger.router)
api_router.include_router(invoice.router)
