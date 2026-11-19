"""Data export and streaming service (Task 19).

Supports:
- Streaming CSV exports for Employees, Payroll Items, and Ledger Lines
- Date-range filtering (start_date, end_date)
- Incremental exports via `since` timestamp filter
"""

import csv
from datetime import date, datetime
from decimal import Decimal
import io
from typing import Any, Generator

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.ledger import JournalEntry, JournalLine
from app.models.payroll import PayrollItem, PayrollRun


def stream_employees_csv(
    session: Session,
    department_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    since: datetime | None = None,
) -> Generator[str, None, None]:
    """Stream employees as CSV rows."""
    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "employee_id", "first_name", "last_name", "work_email", "gender",
        "date_of_birth", "hire_date", "exit_date", "department_id", "role_id",
        "employment_status", "employment_type", "work_mode", "created_at", "updated_at"
    ]
    writer.writerow(headers)
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    stmt = select(Employee).order_by(Employee.employee_id)
    if department_id:
        stmt = stmt.where(Employee.department_id == department_id)
    if start_date:
        stmt = stmt.where(Employee.hire_date >= start_date)
    if end_date:
        stmt = stmt.where(Employee.hire_date <= end_date)
    if since:
        stmt = stmt.where((Employee.updated_at >= since) | (Employee.created_at >= since))

    chunk_size = 200
    offset = 0
    while True:
        chunk = session.scalars(stmt.offset(offset).limit(chunk_size)).all()
        if not chunk:
            break
        for emp in chunk:
            writer.writerow([
                emp.employee_id, emp.first_name, emp.last_name, emp.work_email, emp.gender,
                emp.date_of_birth.isoformat() if emp.date_of_birth else "",
                emp.hire_date.isoformat() if emp.hire_date else "",
                emp.exit_date.isoformat() if emp.exit_date else "",
                emp.department_id, emp.role_id, emp.employment_status,
                emp.employment_type, emp.work_mode,
                emp.created_at.isoformat() if emp.created_at else "",
                emp.updated_at.isoformat() if emp.updated_at else "",
            ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        offset += chunk_size


def stream_payroll_items_csv(
    session: Session,
    run_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    since: datetime | None = None,
) -> Generator[str, None, None]:
    """Stream payroll calculation rows as CSV matching official column structure."""
    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "payroll_item_id", "run_id", "employee_id", "period_start", "period_end",
        "gross_pay", "basic", "hra", "special_allowance",
        "pf_employee", "esi_employee", "professional_tax", "tds",
        "total_deductions", "net_pay", "employer_cost", "created_at"
    ]
    writer.writerow(headers)
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    stmt = select(PayrollItem).order_by(PayrollItem.period_start, PayrollItem.employee_id)
    if run_id:
        stmt = stmt.where(PayrollItem.run_id == run_id)
    if start_date:
        stmt = stmt.where(PayrollItem.period_start >= start_date)
    if end_date:
        stmt = stmt.where(PayrollItem.period_end <= end_date)
    if since:
        stmt = stmt.where((PayrollItem.updated_at >= since) | (PayrollItem.created_at >= since))

    chunk_size = 500
    offset = 0
    while True:
        chunk = session.scalars(stmt.offset(offset).limit(chunk_size)).all()
        if not chunk:
            break
        for pi in chunk:
            writer.writerow([
                pi.payroll_item_id, pi.run_id, pi.employee_id,
                pi.period_start.isoformat() if pi.period_start else "",
                pi.period_end.isoformat() if pi.period_end else "",
                f"{pi.gross_pay:.2f}", f"{pi.basic:.2f}", f"{pi.hra:.2f}",
                f"{pi.special_allowance:.2f}", f"{pi.pf_employee:.2f}",
                f"{pi.esi_employee:.2f}", f"{pi.professional_tax:.2f}",
                f"{pi.tds:.2f}", f"{pi.total_deductions:.2f}",
                f"{pi.net_pay:.2f}", f"{pi.employer_cost:.2f}",
                pi.created_at.isoformat() if pi.created_at else "",
            ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        offset += chunk_size


def stream_ledger_csv(
    session: Session,
    account_code: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    since: datetime | None = None,
) -> Generator[str, None, None]:
    """Stream posted journal entry lines as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "entry_id", "entry_date", "source_type", "source_id", "status",
        "line_no", "account_code", "debit", "credit", "cost_center_department_id",
        "description"
    ]
    writer.writerow(headers)
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)

    stmt = (
        select(JournalLine, JournalEntry)
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.entry_id)
        .where(JournalEntry.status == "POSTED")
        .order_by(JournalEntry.entry_date, JournalLine.entry_id, JournalLine.line_no)
    )
    if account_code:
        stmt = stmt.where(JournalLine.account_code == account_code)
    if start_date:
        stmt = stmt.where(JournalEntry.entry_date >= start_date)
    if end_date:
        stmt = stmt.where(JournalEntry.entry_date <= end_date)
    if since:
        stmt = stmt.where(
            (JournalEntry.created_at >= since.isoformat())
            | (JournalEntry.entry_date >= since.date())
        )

    chunk_size = 500
    offset = 0
    while True:
        chunk = session.execute(stmt.offset(offset).limit(chunk_size)).all()
        if not chunk:
            break
        for jl, je in chunk:
            writer.writerow([
                je.entry_id, je.entry_date.isoformat() if je.entry_date else "",
                je.source_type, je.source_id, je.status,
                jl.line_no, jl.account_code, f"{jl.debit:.2f}", f"{jl.credit:.2f}",
                jl.cost_center_department_id or "", je.description or ""
            ])
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)
        offset += chunk_size


def get_incremental_changes(session: Session, since: datetime) -> dict[str, Any]:
    """Return count and list of entity changes created or modified since a given timestamp."""
    emp_changes = session.scalars(
        select(Employee.employee_id).where((Employee.updated_at >= since) | (Employee.created_at >= since))
    ).all()

    payroll_changes = session.scalars(
        select(PayrollItem.payroll_item_id).where((PayrollItem.updated_at >= since) | (PayrollItem.created_at >= since))
    ).all()

    ledger_changes = session.scalars(
        select(JournalEntry.entry_id).where(
            (JournalEntry.created_at >= since.isoformat())
            | (JournalEntry.entry_date >= since.date())
        )
    ).all()

    return {
        "since": since.isoformat(),
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "employees_changed": len(emp_changes),
            "payroll_items_changed": len(payroll_changes),
            "journal_entries_changed": len(ledger_changes),
        },
        "changed_employees": list(emp_changes),
        "changed_payroll_items": list(payroll_changes),
        "changed_journal_entries": list(ledger_changes),
    }


def csv_stream_to_xlsx_bytes(csv_chunks: Generator[str, None, None], sheet_name: str = "Export") -> bytes:
    """Convert a streamed CSV generator into an Excel (.xlsx) workbook using write-only mode."""
    from openpyxl import Workbook

    wb = Workbook(write_only=True)
    ws = wb.create_sheet(title=sheet_name[:31])

    buffer = ""
    for chunk in csv_chunks:
        buffer += chunk
        lines = buffer.splitlines(keepends=True)
        if lines and not lines[-1].endswith(("\n", "\r")):
            buffer = lines.pop()
        else:
            buffer = ""
        if lines:
            reader = csv.reader(io.StringIO("".join(lines)))
            for row in reader:
                ws.append(row)
    if buffer.strip():
        reader = csv.reader(io.StringIO(buffer))
        for row in reader:
            ws.append(row)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
