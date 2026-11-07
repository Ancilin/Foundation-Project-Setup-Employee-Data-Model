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
    Department,
    Employee,
    EmployeeAssignment,
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

    print(f"Exported {len(rows):>5} rows to {out_path.name}")
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
            "check_in",
            "check_out",
            "hours_worked",
            "overtime_hours",
            "late_flag",
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
