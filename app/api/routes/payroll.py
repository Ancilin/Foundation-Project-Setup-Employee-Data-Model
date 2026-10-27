"""Payroll HTTP routes: calculate employee month pay (LF-07)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.payroll import PayrollCalculateRequest, PayrollItemRead
from app.services import payroll_service

router = APIRouter(prefix="/payroll", tags=["Payroll"])


@router.post("/calculate", response_model=PayrollItemRead)
def calculate_payroll_for_employee_month(
    payload: PayrollCalculateRequest,
    db: Session = Depends(get_db),
):
    """Calculate full gross-to-net pay for an employee and month."""
    return payroll_service.calculate_employee_month_from_db(
        session=db,
        employee_id=payload.employee_id,
        month=payload.month,
        variable_pay=payload.variable_pay,
        variable_pay_type=payload.variable_pay_type,
        other_deductions=payload.other_deductions,
    )
