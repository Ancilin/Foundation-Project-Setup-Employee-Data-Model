"""Export database tables to clean CSV files in exports/ directory.

Usage:
    python -m scripts.export_csv
"""

import csv
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db.session import get_engine  # noqa: E402
from app.models import (  # noqa: E402
    Attendance,
    ChartOfAccount,
    Client,
    Department,
    Employee,
    EmployeeAssignment,
    Holiday,
    Invoice,
    InvoiceItem,
    InvoicePayment,
    JournalEntry,
    JournalLine,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    PayrollItem,
    PayrollRun,
    Role,
    Salary,
    SalaryComponent,
    SalaryRevision,
    SalaryStructure,
)

EXPORTS_DIR = ROOT / "exports"


def _clean_val(val):
    if val is None:
        return ""
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return str(val)
    return str(val)


def export_table(
    session: Session, model, filename: str, columns: list[str], target_dir: Path = EXPORTS_DIR
) -> int:
    """Export a SQLAlchemy model to a CSV file."""
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / filename

    stmt = select(model)
    rows = session.scalars(stmt).all()

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for r in rows:
            writer.writerow([_clean_val(getattr(r, col, None)) for col in columns])

    print(f"Exported {len(rows):>6} rows to {out_path.name}")
    return len(rows)


def _do_export(session: Session, target_dir: Path = EXPORTS_DIR) -> dict[str, int]:
    results = {}

    # 1. Employees
    results["employees"] = export_table(
        session,
        Employee,
        "employees.csv",
        [
            "employee_id",
            "first_name",
            "last_name",
            "work_email",
            "gender",
            "date_of_birth",
            "hire_date",
            "exit_date",
            "employment_status",
            "employment_type",
            "department_id",
            "role_id",
            "manager_id",
            "work_location",
            "work_mode",
            "is_active",
            "created_at",
            "updated_at",
        ],
        target_dir=target_dir,
    )

    # 2. Salaries
    results["salaries"] = export_table(
        session,
        Salary,
        "salaries.csv",
        [
            "salary_id",
            "employee_id",
            "monthly_gross",
            "basic",
            "hra",
            "special_allowance",
            "annual_ctc",
            "effective_from",
            "effective_to",
            "is_active",
            "created_at",
        ],
        target_dir=target_dir,
    )

    # 3. Attendance
    results["attendance"] = export_table(
        session,
        Attendance,
        "attendance.csv",
        [
            "attendance_id",
            "employee_id",
            "attendance_date",
            "weekday",
            "status",
            "leave_type_code",
            "check_in",
            "check_out",
            "hours_worked",
            "overtime_hours",
            "late_flag",
            "source",
            "data_quality_flag",
            "department_id",
            "is_active",
        ],
        target_dir=target_dir,
    )

    # 4. Departments
    results["departments"] = export_table(
        session,
        Department,
        "departments.csv",
        ["department_id", "department_name", "cost_center", "description", "is_active"],
        target_dir=target_dir,
    )

    # 5. Roles
    results["roles"] = export_table(
        session,
        Role,
        "roles.csv",
        [
            "role_id",
            "department_id",
            "role_title",
            "level",
            "grade",
            "band_min_annual",
            "band_mid_annual",
            "band_max_annual",
            "overtime_eligible",
            "is_active",
        ],
        target_dir=target_dir,
    )

    # 6. Employee Assignments
    results["employee_assignments"] = export_table(
        session,
        EmployeeAssignment,
        "employee_assignments.csv",
        [
            "assignment_id",
            "employee_id",
            "effective_from",
            "effective_to",
            "department_id",
            "role_id",
            "job_level",
            "manager_id",
            "change_reason",
        ],
        target_dir=target_dir,
    )

    # 7. Salary Components
    results["salary_components"] = export_table(
        session,
        SalaryComponent,
        "salary_components.csv",
        ["component_id", "component_name", "component_type", "taxable", "calculation_rule", "is_fixed"],
        target_dir=target_dir,
    )

    # 8. Salary Structures
    results["salary_structures"] = export_table(
        session,
        SalaryStructure,
        "salary_structures.csv",
        [
            "structure_id",
            "employee_id",
            "component_id",
            "component_name",
            "component_type",
            "monthly_amount",
            "effective_from",
            "effective_to",
            "revision_id",
        ],
        target_dir=target_dir,
    )

    # 9. Salary Revisions
    results["salary_revisions"] = export_table(
        session,
        SalaryRevision,
        "salary_revisions.csv",
        [
            "revision_id",
            "employee_id",
            "effective_from",
            "revision_reason",
            "previous_annual_fixed",
            "new_annual_fixed",
            "pct_change",
            "role_id_after",
            "approved_by",
        ],
        target_dir=target_dir,
    )

    # 10. Holidays (LF-06)
    results["holidays"] = export_table(
        session,
        Holiday,
        "holidays.csv",
        ["holiday_date", "holiday_name", "holiday_type", "weekday", "falls_on_weekend", "calendar_note"],
        target_dir=target_dir,
    )

    # 11. Leave Types (LF-06)
    results["leave_types"] = export_table(
        session,
        LeaveType,
        "leave_types.csv",
        [
            "leave_type_code",
            "leave_type_name",
            "pay_type",
            "annual_quota_days",
            "prorated_for_joiners",
            "carry_forward_allowed",
            "max_carry_forward_days",
            "policy_note",
        ],
        target_dir=target_dir,
    )

    # 12. Leave Balances (LF-06)
    results["leave_balances"] = export_table(
        session,
        LeaveBalance,
        "leave_balances.csv",
        [
            "employee_id",
            "as_of_date",
            "financial_year",
            "cl_entitlement",
            "cl_used",
            "cl_balance",
            "sl_entitlement",
            "sl_used",
            "sl_balance",
            "el_used_fy",
            "el_balance",
            "pending_days",
        ],
        target_dir=target_dir,
    )

    # 13. Leave Requests (LF-06)
    results["leave_requests"] = export_table(
        session,
        LeaveRequest,
        "leave_requests.csv",
        [
            "leave_request_id",
            "employee_id",
            "leave_type_code",
            "start_date",
            "end_date",
            "days",
            "reason",
            "status",
            "applied_on",
            "approver_id",
            "decided_on",
        ],
        target_dir=target_dir,
    )

    # 14. Payroll Runs (LF-07 / LF-09)
    results["payroll_runs"] = export_table(
        session,
        PayrollRun,
        "payroll_runs.csv",
        [
            "run_id",
            "period_start",
            "period_end",
            "pay_date",
            "employees_paid",
            "total_gross",
            "total_deductions",
            "total_net",
            "total_employer_contributions",
            "total_employer_cost",
            "status",
            "run_by",
            "approved_by",
            "created_at",
            "approved_at",
            "idempotency_key",
            "journal_entry_id",
            "calculation_version",
        ],
        target_dir=target_dir,
    )

    # 15. Payroll Items (LF-07 / LF-09)
    results["payroll_items"] = export_table(
        session,
        PayrollItem,
        "payroll_items.csv",
        [
            "payroll_item_id",
            "run_id",
            "employee_id",
            "period_start",
            "period_end",
            "department_id",
            "role_id",
            "calendar_days",
            "days_employed",
            "lop_days",
            "payable_days",
            "monthly_fixed_gross",
            "basic",
            "hra",
            "conveyance",
            "medical",
            "special_allowance",
            "earned_fixed_pay",
            "overtime_hours_paid",
            "overtime_pay",
            "variable_pay",
            "variable_pay_type",
            "gross_pay",
            "pf_employee",
            "esi_employee",
            "professional_tax",
            "tds",
            "other_deductions",
            "total_deductions",
            "net_pay",
            "pf_employer",
            "esi_employer",
            "employer_cost",
            "calculation_note",
        ],
        target_dir=target_dir,
    )

    # 16. Chart of Accounts (LF-09)
    results["chart_of_accounts"] = export_table(
        session,
        ChartOfAccount,
        "chart_of_accounts.csv",
        [
            "account_code",
            "account_name",
            "account_type",
            "normal_balance",
            "parent_code",
            "is_group",
            "statement",
            "is_active",
        ],
        target_dir=target_dir,
    )

    # 17. Journal Entries (LF-09)
    results["journal_entries"] = export_table(
        session,
        JournalEntry,
        "journal_entries.csv",
        [
            "entry_id",
            "entry_date",
            "posting_period",
            "financial_year",
            "description",
            "source_type",
            "source_id",
            "status",
            "total_debit",
            "total_credit",
            "reversal_of_source_id",
            "created_by",
            "created_at",
        ],
        target_dir=target_dir,
    )

    # 18. Journal Lines (LF-09)
    results["journal_lines"] = export_table(
        session,
        JournalLine,
        "journal_lines.csv",
        [
            "line_id",
            "entry_id",
            "line_no",
            "account_code",
            "debit",
            "credit",
            "cost_center_department_id",
            "line_description",
        ],
        target_dir=target_dir,
    )

    # 19. Clients (LF-10)
    results["clients"] = export_table(
        session,
        Client,
        "clients.csv",
        [
            "client_id",
            "client_name",
            "industry",
            "city",
            "state_or_region",
            "country",
            "client_type",
            "gst_registration",
            "payment_terms_days",
            "payment_behaviour",
            "primary_service_line",
            "contact_email",
            "onboarded_on",
            "is_active",
        ],
        target_dir=target_dir,
    )

    # 20. Invoices (LF-10)
    results["invoices"] = export_table(
        session,
        Invoice,
        "invoices.csv",
        [
            "invoice_id",
            "invoice_number",
            "client_id",
            "invoice_date",
            "due_date",
            "service_line_account",
            "currency",
            "subtotal",
            "gst_rate_percent",
            "gst_amount",
            "total_amount",
            "amount_paid",
            "balance_due",
            "status",
            "last_payment_date",
            "po_number",
            "carried_in_from_prior_period",
            "created_by",
            "created_at",
            "ledger_entry_id",
        ],
        target_dir=target_dir,
    )

    # 21. Invoice Items (LF-10)
    results["invoice_items"] = export_table(
        session,
        InvoiceItem,
        "invoice_items.csv",
        [
            "invoice_item_id",
            "invoice_id",
            "line_no",
            "description",
            "quantity",
            "unit_price",
            "amount",
            "revenue_account",
        ],
        target_dir=target_dir,
    )

    # 22. Invoice Payments (LF-10)
    results["invoice_payments"] = export_table(
        session,
        InvoicePayment,
        "invoice_payments.csv",
        [
            "payment_id",
            "invoice_id",
            "payment_date",
            "amount",
            "payment_mode",
            "reference_no",
            "received_by",
            "ledger_entry_id",
        ],
        target_dir=target_dir,
    )

    return results


def export_all_to_csv(
    session: Session | None = None, target_dir: Path | None = None
) -> dict[str, int]:
    """Export database tables to CSV."""
    dst = target_dir or EXPORTS_DIR
    if session is not None:
        return _do_export(session, target_dir=dst)
    engine = get_engine()
    with Session(engine) as s:
        return _do_export(s, target_dir=dst)


if __name__ == "__main__":
    export_all_to_csv()
