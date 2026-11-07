"""Tests for Task 8 (LF-08): Payslip JSON & PDF generator, Indian number formatting, and ownership checks."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
import pandas as pd
import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import (
    Attendance,
    Base,
    Department,
    Employee,
    PayrollItem,
    PayrollRun,
    Role,
    SalaryStructure,
    TaxSlab,
)
from app.services.payslip_service import format_inr, generate_payslip_pdf, number_to_indian_words

ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = ROOT / "data" / "csv"


@pytest.fixture(scope="module")
def payslip_test_client():
    """Seed an isolated SQLite database with the 3 benchmark employees (EMP-0002, EMP-0011, EMP-0049) for PR-2025-04."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    target_emps = {"EMP-0002", "EMP-0011", "EMP-0049"}

    with TestingSessionLocal() as session:
        # 1. Departments
        df_dept = pd.read_csv(CSV_DIR / "departments.csv")
        for _, r in df_dept.iterrows():
            session.add(
                Department(
                    department_id=str(r["department_id"]).strip(),
                    department_name=str(r["department_name"]).strip(),
                    cost_center=str(r["cost_center"]).strip(),
                    description=str(r["description"]).strip() if pd.notna(r.get("description")) else None,
                )
            )

        # 2. Roles
        df_role = pd.read_csv(CSV_DIR / "roles.csv")
        for _, r in df_role.iterrows():
            session.add(
                Role(
                    role_id=str(r["role_id"]).strip(),
                    department_id=str(r["department_id"]).strip(),
                    role_title=str(r["role_title"]).strip(),
                    level=int(r["level"]),
                    grade=str(r["grade"]).strip(),
                    band_min_annual=float(r["band_min_annual"]),
                    band_mid_annual=float(r["band_mid_annual"]),
                    band_max_annual=float(r["band_max_annual"]),
                    overtime_eligible=(str(r["overtime_eligible"]).strip().upper() == "Y"),
                )
            )

        # 3. Employees
        df_emp = pd.read_csv(CSV_DIR / "employees.csv")
        df_emp = df_emp[df_emp["employee_id"].isin(target_emps)]
        for _, r in df_emp.iterrows():
            eid = str(r["employee_id"]).strip()
            session.add(
                Employee(
                    employee_id=eid,
                    first_name="Test",
                    last_name=eid,
                    work_email=f"{eid.lower()}@znova-demo.example",
                    gender=str(r["gender"]).strip(),
                    date_of_birth=date.fromisoformat(str(r["date_of_birth"])[:10]),
                    hire_date=date.fromisoformat(str(r["hire_date"])[:10]),
                    exit_date=date.fromisoformat(str(r["exit_date"])[:10]) if pd.notna(r.get("exit_date")) else None,
                    employment_status=str(r["employment_status"]).strip(),
                    employment_type=str(r["employment_type"]).strip(),
                    department_id=str(r["department_id"]).strip(),
                    role_id=str(r["role_id"]).strip(),
                    manager_id=None,
                    work_location=str(r["work_location"]).strip(),
                    work_mode=str(r["work_mode"]).strip(),
                )
            )

        # 4. Salary Structures
        df_st = pd.read_csv(CSV_DIR / "salary_structures.csv")
        df_st = df_st[df_st["employee_id"].isin(target_emps)]
        for _, r in df_st.iterrows():
            session.add(
                SalaryStructure(
                    structure_id=str(r["structure_id"]).strip(),
                    employee_id=str(r["employee_id"]).strip(),
                    component_id=str(r["component_id"]).strip(),
                    component_name=str(r["component_name"]).strip(),
                    component_type=str(r["component_type"]).strip(),
                    monthly_amount=Decimal(str(r["monthly_amount"])),
                    effective_from=date.fromisoformat(str(r["effective_from"])[:10]),
                    effective_to=date.fromisoformat(str(r["effective_to"])[:10])
                    if pd.notna(r.get("effective_to"))
                    else None,
                    revision_id=str(r["revision_id"]).strip() if pd.notna(r.get("revision_id")) else None,
                )
            )

        # 5. Tax Slabs
        df_ts = pd.read_csv(CSV_DIR / "tax_slabs.csv")
        for _, r in df_ts.iterrows():
            session.add(
                TaxSlab(
                    slab_id=str(r["slab_id"]).strip(),
                    regime=str(r["regime"]).strip(),
                    financial_year=str(r["financial_year"]).strip(),
                    income_from=Decimal(str(r["income_from"])),
                    income_to=Decimal(str(r["income_to"])) if pd.notna(r.get("income_to")) else None,
                    rate_percent=Decimal(str(r["rate_percent"])),
                    effective_from=date.fromisoformat(str(r["effective_from"])[:10]),
                    note=str(r["note"]).strip() if pd.notna(r.get("note")) else None,
                )
            )

        # 6. Attendance for April 2025
        df_att = pd.read_csv(CSV_DIR / "attendance.csv", low_memory=False)
        df_att = df_att[
            df_att["employee_id"].isin(target_emps)
            & df_att["attendance_date"].astype(str).str.startswith("2025-04")
        ].copy()
        df_att["attendance_date"] = pd.to_datetime(df_att["attendance_date"]).dt.date
        df_att["overtime_hours"] = df_att["overtime_hours"].fillna(0.0)
        df_att["late_flag"] = df_att["late_flag"].fillna("N")
        df_att = df_att.where(pd.notna(df_att), None)
        session.execute(insert(Attendance), df_att.to_dict(orient="records"))

        # 7. PayrollRun & PayrollItems for PR-2025-04
        df_pr = pd.read_csv(CSV_DIR / "payroll_runs.csv")
        pr_row = df_pr[df_pr["run_id"] == "PR-2025-04"].iloc[0]
        session.add(
            PayrollRun(
                run_id="PR-2025-04",
                period_start=date.fromisoformat(str(pr_row["period_start"])[:10]),
                period_end=date.fromisoformat(str(pr_row["period_end"])[:10]),
                pay_date=date.fromisoformat(str(pr_row["pay_date"])[:10]),
                employees_paid=int(pr_row["employees_paid"]),
                total_gross=Decimal(str(pr_row["total_gross"])),
                total_deductions=Decimal(str(pr_row["total_deductions"])),
                total_net=Decimal(str(pr_row["total_net"])),
                total_employer_contributions=Decimal(str(pr_row["total_employer_contributions"])),
                total_employer_cost=Decimal(str(pr_row["total_employer_cost"])),
                status=str(pr_row["status"]).strip(),
            )
        )

        df_pi = pd.read_csv(CSV_DIR / "payroll_items.csv")
        df_pi = df_pi[(df_pi["run_id"] == "PR-2025-04") & (df_pi["employee_id"].isin(target_emps))]
        for _, r in df_pi.iterrows():
            session.add(
                PayrollItem(
                    payroll_item_id=str(r["payroll_item_id"]).strip(),
                    run_id=str(r["run_id"]).strip(),
                    employee_id=str(r["employee_id"]).strip(),
                    period_start=date.fromisoformat(str(r["period_start"])[:10]),
                    period_end=date.fromisoformat(str(r["period_end"])[:10]),
                    department_id=str(r["department_id"]).strip(),
                    role_id=str(r["role_id"]).strip(),
                    calendar_days=int(r["calendar_days"]),
                    days_employed=int(r["days_employed"]),
                    lop_days=Decimal(str(r["lop_days"])),
                    payable_days=Decimal(str(r["payable_days"])),
                    monthly_fixed_gross=Decimal(str(r["monthly_fixed_gross"])),
                    basic=Decimal(str(r["basic"])),
                    hra=Decimal(str(r["hra"])),
                    conveyance=Decimal(str(r["conveyance"])),
                    medical=Decimal(str(r["medical"])),
                    special_allowance=Decimal(str(r["special_allowance"])),
                    earned_fixed_pay=Decimal(str(r["earned_fixed_pay"])),
                    overtime_hours_paid=Decimal(str(r["overtime_hours_paid"])),
                    overtime_pay=Decimal(str(r["overtime_pay"])),
                    variable_pay=Decimal(str(r["variable_pay"])),
                    variable_pay_type=str(r["variable_pay_type"]).strip() if pd.notna(r.get("variable_pay_type")) else None,
                    gross_pay=Decimal(str(r["gross_pay"])),
                    pf_employee=Decimal(str(r["pf_employee"])),
                    esi_employee=Decimal(str(r["esi_employee"])),
                    professional_tax=Decimal(str(r["professional_tax"])),
                    tds=Decimal(str(r["tds"])),
                    other_deductions=Decimal(str(r["other_deductions"])),
                    total_deductions=Decimal(str(r["total_deductions"])),
                    net_pay=Decimal(str(r["net_pay"])),
                    pf_employer=Decimal(str(r["pf_employer"])),
                    esi_employer=Decimal(str(r["esi_employer"])),
                    employer_cost=Decimal(str(r["employer_cost"])),
                    calculation_note=str(r["calculation_note"]).strip() if pd.notna(r.get("calculation_note")) else None,
                )
            )
        session.commit()

    def _override_get_db():
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_indian_number_formatting_and_words():
    """Verify Indian currency formatting (1,23,456.00) and Indian Rupees in words."""
    assert format_inr(Decimal("0")) == "0.00"
    assert format_inr(Decimal("500")) == "500.00"
    assert format_inr(Decimal("1800.00")) == "1,800.00"
    assert format_inr(Decimal("123456")) == "1,23,456.00"
    assert format_inr(Decimal("158504.61")) == "1,58,504.61"
    assert format_inr(Decimal("123456789.50")) == "12,34,56,789.50"

    words = number_to_indian_words(Decimal("158504.61"))
    assert words == "Rupees One Lakh Fifty-Eight Thousand Five Hundred Four and Sixty-One Paise Only"


def test_stranger_is_refused_payslip_access(payslip_test_client: TestClient):
    """Only the owner or HR may fetch a payslip. A stranger employee or anonymous user gets 403 Forbidden."""
    # 1. Stranger employee EMP-0011 tries to fetch EMP-0002's payslip via query param
    resp_stranger = payslip_test_client.get(
        "/payslips/EMP-0002/PR-2025-04",
        params={"requester_id": "EMP-0011", "requester_role": "EMPLOYEE"},
    )
    assert resp_stranger.status_code == 403
    assert resp_stranger.json()["error_code"] == "FORBIDDEN"

    # 2. Stranger employee EMP-0011 tries to fetch EMP-0002's PDF via headers
    resp_stranger_pdf = payslip_test_client.get(
        "/payslips/EMP-0002/PR-2025-04/pdf",
        headers={"X-Employee-Id": "EMP-0011", "X-Role": "EMPLOYEE"},
    )
    assert resp_stranger_pdf.status_code == 403

    # 3. Unauthenticated caller without identity headers/params is also refused
    resp_anon = payslip_test_client.get("/payslips/EMP-0002/PR-2025-04")
    assert resp_anon.status_code == 403

    # 4. Owner EMP-0002 is allowed (200 OK)
    resp_owner = payslip_test_client.get(
        "/payslips/EMP-0002/PR-2025-04",
        headers={"X-Employee-Id": "EMP-0002", "X-Role": "EMPLOYEE"},
    )
    assert resp_owner.status_code == 200

    # 5. HR user is allowed to fetch any employee's payslip (200 OK)
    resp_hr = payslip_test_client.get(
        "/payslips/EMP-0002/PR-2025-04",
        headers={"X-Employee-Id": "EMP-0099", "X-Role": "HR"},
    )
    assert resp_hr.status_code == 200


@pytest.mark.parametrize(
    "employee_id,expected_gross_fmt,expected_ded_fmt,expected_net_fmt",
    [
        ("EMP-0002", "1,79,130.40", "20,625.79", "1,58,504.61"),
        ("EMP-0011", "36,969.21", "1,334.69", "35,634.52"),
        ("EMP-0049", "8,12,855.00", "2,18,539.09", "5,94,315.91"),
    ],
)
def test_three_payslips_and_pdfs_match_payroll_items(
    payslip_test_client: TestClient,
    employee_id: str,
    expected_gross_fmt: str,
    expected_ded_fmt: str,
    expected_net_fmt: str,
):
    """Compare 3 employees' JSON payslips and generated PDFs against payroll_items.csv."""
    df_pi = pd.read_csv(CSV_DIR / "payroll_items.csv")
    csv_row = df_pi[(df_pi["employee_id"] == employee_id) & (df_pi["run_id"] == "PR-2025-04")].iloc[0]

    # Fetch JSON payslip as owner
    resp = payslip_test_client.get(
        f"/payslips/{employee_id}/PR-2025-04",
        params={"requester_id": employee_id},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Check exact Decimal parity against payroll_items.csv
    for key in [
        "basic",
        "hra",
        "conveyance",
        "medical",
        "special_allowance",
        "earned_fixed_pay",
        "overtime_pay",
        "variable_pay",
        "gross_pay",
        "pf_employee",
        "esi_employee",
        "professional_tax",
        "tds",
        "other_deductions",
        "total_deductions",
        "net_pay",
    ]:
        assert Decimal(str(data[key])) == Decimal(str(csv_row[key])).quantize(Decimal("0.01")), f"Mismatch on {key}"

    # Check Indian number formatting
    assert data["gross_pay_formatted"] == expected_gross_fmt
    assert data["total_deductions_formatted"] == expected_ded_fmt
    assert data["net_pay_formatted"] == expected_net_fmt

    # Fetch PDF payslip via /pdf endpoint
    pdf_resp = payslip_test_client.get(
        f"/payslips/{employee_id}/PR-2025-04/pdf",
        params={"requester_id": employee_id},
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF-")
    assert len(pdf_resp.content) > 1500
