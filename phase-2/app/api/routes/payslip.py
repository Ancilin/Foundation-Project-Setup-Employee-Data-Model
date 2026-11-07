"""Payslip API endpoints (LF-08): JSON data and PDF generation with ownership enforcement."""

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.payslip import PayslipResponse
from app.services.payslip_service import generate_payslip_pdf, get_payslip_data

router = APIRouter(prefix="/payslips", tags=["Payslips"])


def _resolve_caller(
    requester_id: str | None = Query(default=None, description="Caller employee_id for ownership verification"),
    requester_role: str | None = Query(default=None, description="Caller role (e.g., EMPLOYEE, HR, ADMIN)"),
    x_employee_id: str | None = Header(default=None, alias="X-Employee-Id"),
    x_user_employee_id: str | None = Header(default=None, alias="X-User-Employee-Id"),
    x_role: str | None = Header(default=None, alias="X-Role"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
) -> tuple[str | None, str | None]:
    eff_emp_id = requester_id or x_employee_id or x_user_employee_id
    eff_role = requester_role or x_role or x_user_role
    return eff_emp_id, eff_role


@router.get("/{employee_id}/{run_id}", response_model=PayslipResponse)
def fetch_payslip(
    employee_id: str,
    run_id: str,
    format: str = Query(default="json", description="Response format: 'json' or 'pdf'"),
    caller: tuple[str | None, str | None] = Depends(_resolve_caller),
    db: Session = Depends(get_db),
):
    """Return payslip figures from the payroll engine as JSON (default) or PDF (?format=pdf).
    Only the payslip owner or HR/ADMIN may fetch a payslip.
    """
    req_emp_id, req_role = caller
    payslip_data = get_payslip_data(
        session=db,
        employee_id=employee_id,
        run_id=run_id,
        requester_id=req_emp_id,
        requester_role=req_role,
    )
    if format.strip().lower() == "pdf":
        pdf_bytes = generate_payslip_pdf(payslip_data)
        filename = f"payslip_{employee_id}_{payslip_data['run_id']}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )
    return payslip_data


@router.get("/{employee_id}/{run_id}/pdf")
def fetch_payslip_pdf(
    employee_id: str,
    run_id: str,
    caller: tuple[str | None, str | None] = Depends(_resolve_caller),
    db: Session = Depends(get_db),
) -> Response:
    """Generate and return the PDF payslip for an employee and payroll run.
    Only the payslip owner or HR/ADMIN may fetch a payslip.
    """
    req_emp_id, req_role = caller
    payslip_data = get_payslip_data(
        session=db,
        employee_id=employee_id,
        run_id=run_id,
        requester_id=req_emp_id,
        requester_role=req_role,
    )
    pdf_bytes = generate_payslip_pdf(payslip_data)
    filename = f"payslip_{employee_id}_{payslip_data['run_id']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
