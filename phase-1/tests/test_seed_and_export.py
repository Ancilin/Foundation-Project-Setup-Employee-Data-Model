"""Tests for Master Dataset Seed Pipeline, Faker Generation, and CSV Exports."""

from pathlib import Path
from sqlalchemy import select

from app.models import Attendance, Department, Employee, Role, Salary
from scripts.export_csv import export_all_to_csv, EXPORTS_DIR
from scripts.seed import seed_master_dataset, ROOT


def test_seed_pipeline_and_linked_data(session):
    """Seed a subset into the test session, verify linked tables, and check idempotency."""
    xlsx_path = ROOT / "01_LedgerForge_Python_Master_Dataset.xlsx"
    assert xlsx_path.exists(), "Dataset xlsx file must exist"

    # 1. Run seed pipeline on test session
    res1 = seed_master_dataset(
        xlsx_path, attendance_days=5, employee_limit=15, do_export=False, session=session
    )
    assert res1["departments"] > 0
    assert res1["roles"] > 0
    assert res1["employees"] > 0
    assert res1["salaries"] > 0
    assert res1["attendance"] > 0

    # 2. Verify linked salary and attendance records
    emps = session.scalars(select(Employee)).all()
    assert len(emps) > 0

    for emp in emps:
        sal = session.scalar(select(Salary).where(Salary.employee_id == emp.employee_id))
        assert sal is not None, f"Employee {emp.employee_id} must have a linked salary"
        assert sal.monthly_gross > 0
        assert sal.basic > 0
        assert sal.hra > 0
        assert sal.special_allowance >= 0

        # Verify role band
        role = session.get(Role, emp.role_id)
        if role:
            assert float(sal.annual_ctc) >= float(role.band_min_annual) - 1.0
            assert float(sal.annual_ctc) <= float(role.band_max_annual) + 1.0

    # 3. Test idempotency: re-running should not crash or duplicate records
    res2 = seed_master_dataset(
        xlsx_path, attendance_days=5, employee_limit=15, do_export=False, session=session
    )
    assert res1["departments"] == res2["departments"]
    assert res1["roles"] == res2["roles"]
    assert res1["employees"] == res2["employees"]
    assert res1["salaries"] == res2["salaries"]
    assert res1["attendance"] == res2["attendance"]


def test_export_all_to_csv_creates_valid_files(session, tmp_path):
    xlsx_path = ROOT / "01_LedgerForge_Python_Master_Dataset.xlsx"
    seed_master_dataset(
        xlsx_path, attendance_days=3, employee_limit=10, do_export=False, session=session
    )

    test_export_dir = tmp_path / "exports"
    counts = export_all_to_csv(session=session, target_dir=test_export_dir)

    for name in ["employees", "salaries", "attendance", "departments", "roles"]:
        assert name in counts
        csv_file = test_export_dir / f"{name}.csv"
        assert csv_file.exists()
        lines = csv_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 2, f"CSV {csv_file.name} must have header and at least 1 row"

    # Spot check employees.csv
    emp_lines = (test_export_dir / "employees.csv").read_text(encoding="utf-8").splitlines()
    assert "employee_id,first_name,last_name" in emp_lines[0]
    assert "test123" not in emp_lines[1].lower()
