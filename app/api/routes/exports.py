"""Export HTTP routes: streaming CSV & Excel (.xlsx) exports for Employees, Payroll, Ledger, and incremental changes (Task 19)."""

from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.user import User
from app.services import export_service

router = APIRouter(prefix="/exports", tags=["Exports & Data Streaming"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get(
    "/employees",
    summary="Export Employees dataset (streaming CSV or Excel)",
    description="Streams employee master records with optional filtering by department, hire date range, or incremental changes since a timestamp.",
    responses={
        200: {
            "content": {"text/csv": {"example": "employee_id,first_name,last_name,work_email...\nEMP-0001,Ganesh,Murthy,..."}},
            "description": "Streamed CSV or Excel (.xlsx) file of employees.",
        }
    },
)
def export_employees(
    department_id: str | None = Query(default=None, description="Filter by department ID (e.g. D-ENG)"),
    start_date: date | None = Query(default=None, description="Filter hire_date >= YYYY-MM-DD"),
    end_date: date | None = Query(default=None, description="Filter hire_date <= YYYY-MM-DD"),
    since: datetime | None = Query(default=None, description="Incremental export: return only records modified since this timestamp (ISO-8601)"),
    format: Literal["csv", "xlsx"] = Query(default="csv", description="Export format: csv (streaming) or xlsx (Excel)"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Export employees as streaming CSV or Excel (.xlsx) download."""
    generator = export_service.stream_employees_csv(
        db, department_id=department_id, start_date=start_date, end_date=end_date, since=since
    )
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if format == "xlsx":
        payload = export_service.csv_stream_to_xlsx_bytes(generator, sheet_name="Employees")
        return Response(
            content=payload,
            media_type=XLSX_MEDIA_TYPE,
            headers={"Content-Disposition": f"attachment; filename=employees_export_{stamp}.xlsx"},
        )
    return StreamingResponse(
        generator,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=employees_export_{stamp}.csv"},
    )


@router.get(
    "/payroll",
    summary="Export Payroll calculation rows (streaming CSV or Excel)",
    description="Streams detailed gross-to-net payroll items matching official dataset structure with date range, run_id, and incremental filters.",
    responses={
        200: {
            "content": {"text/csv": {"example": "payroll_item_id,run_id,employee_id,period_start,gross_pay,net_pay...\nPI-00001,PR-2025-04,EMP-0002,..."}},
            "description": "Streamed CSV or Excel (.xlsx) file of payroll items.",
        }
    },
)
def export_payroll(
    run_id: str | None = Query(default=None, description="Filter by specific payroll run (e.g. PR-2025-04)"),
    start_date: date | None = Query(default=None, description="Filter period start >= YYYY-MM-DD"),
    end_date: date | None = Query(default=None, description="Filter period end <= YYYY-MM-DD"),
    since: datetime | None = Query(default=None, description="Incremental export: modified since ISO-8601 timestamp"),
    format: Literal["csv", "xlsx"] = Query(default="csv", description="Export format: csv (streaming) or xlsx (Excel)"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Export payroll items as streaming CSV or Excel (.xlsx) download."""
    generator = export_service.stream_payroll_items_csv(
        db, run_id=run_id, start_date=start_date, end_date=end_date, since=since
    )
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if format == "xlsx":
        payload = export_service.csv_stream_to_xlsx_bytes(generator, sheet_name="Payroll")
        return Response(
            content=payload,
            media_type=XLSX_MEDIA_TYPE,
            headers={"Content-Disposition": f"attachment; filename=payroll_export_{stamp}.xlsx"},
        )
    return StreamingResponse(
        generator,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=payroll_export_{stamp}.csv"},
    )


@router.get(
    "/ledger",
    summary="Export Posted Ledger Journal Lines (streaming CSV or Excel)",
    description="Streams posted double-entry journal lines with date range, account code, and incremental filters.",
    responses={
        200: {
            "content": {"text/csv": {"example": "entry_id,entry_date,source_type,account_code,debit,credit...\nJE-000105,2025-04-30,PAYROLL_RUN,5001,1523000.00,0.00"}},
            "description": "Streamed CSV or Excel (.xlsx) file of posted journal lines.",
        }
    },
)
def export_ledger(
    account_code: int | None = Query(default=None, description="Filter by account code (e.g. 5001)"),
    start_date: date | None = Query(default=None, description="Filter entry date >= YYYY-MM-DD"),
    end_date: date | None = Query(default=None, description="Filter entry date <= YYYY-MM-DD"),
    since: datetime | None = Query(default=None, description="Incremental export: modified since ISO-8601 timestamp"),
    format: Literal["csv", "xlsx"] = Query(default="csv", description="Export format: csv (streaming) or xlsx (Excel)"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Export posted journal lines as streaming CSV or Excel (.xlsx) download."""
    generator = export_service.stream_ledger_csv(
        db, account_code=account_code, start_date=start_date, end_date=end_date, since=since
    )
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if format == "xlsx":
        payload = export_service.csv_stream_to_xlsx_bytes(generator, sheet_name="Ledger")
        return Response(
            content=payload,
            media_type=XLSX_MEDIA_TYPE,
            headers={"Content-Disposition": f"attachment; filename=ledger_export_{stamp}.xlsx"},
        )
    return StreamingResponse(
        generator,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=ledger_export_{stamp}.csv"},
    )


@router.get(
    "/changes",
    summary="Incremental Export: Changes manifest since timestamp",
    description="Returns list and count of all records modified or created since the given timestamp.",
)
def export_changes(
    since: datetime = Query(description="Incremental timestamp cutoff in ISO-8601 format (e.g. 2026-11-01T00:00:00)"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Return delta changes across entities since the provided timestamp."""
    return export_service.get_incremental_changes(db, since=since)
