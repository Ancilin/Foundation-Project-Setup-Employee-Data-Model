"""Tests for Task 20 Final Challenge: Executive Departmental Payroll Cost & Statutory Breakdown Report."""

from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import create_app
from app.models.base import Base
from app.models.department import Department
from app.models.employee import Employee
from app.models.payroll import PayrollItem, PayrollRun
from app.models.role import Role
from app.models.user import User


@pytest.fixture
def dept_report_client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        d_eng = Department(department_id="D-ENG", department_name="Engineering", cost_center="CC-ENG", is_active=True)
        d_fin = Department(department_id="D-FIN", department_name="Finance", cost_center="CC-FIN", is_active=True)
        r_eng = Role(
            role_id="R-SWE", department_id="D-ENG", role_title="Senior Engineer",
            level=2, grade="L2", band_min_annual=1200000, band_mid_annual=1800000, band_max_annual=2400000, is_active=True
        )
        r_fin = Role(
            role_id="R-ACC", department_id="D-FIN", role_title="Senior Accountant",
            level=2, grade="L2", band_min_annual=800000, band_mid_annual=1200000, band_max_annual=1600000, is_active=True
        )
        session.add_all([d_eng, d_fin, r_eng, r_fin])
        session.flush()

        e1 = Employee(
            employee_id="EMP-1001", first_name="Asha", last_name="Menon",
            work_email="asha.menon@znova-demo.example", gender="Female",
            date_of_birth=date(1992, 4, 12), hire_date=date(2023, 1, 10),
            department_id="D-ENG", role_id="R-SWE",
            employment_status="Active", employment_type="Permanent",
            work_location="Bengaluru", work_mode="Hybrid",
        )
        e2 = Employee(
            employee_id="EMP-1002", first_name="Rohan", last_name="Desai",
            work_email="rohan.desai@znova-demo.example", gender="Male",
            date_of_birth=date(1990, 9, 20), hire_date=date(2022, 6, 1),
            department_id="D-FIN", role_id="R-ACC",
            employment_status="Active", employment_type="Permanent",
            work_location="Mumbai", work_mode="Onsite",
        )
        admin_u = User(
            user_id="U-ADM", employee_id="EMP-1001", username="admin", role="ADMIN",
            password_hash=hash_password("LedgerForge2025!"), is_active="Y",
        )
        emp_u = User(
            user_id="U-EMP", employee_id="EMP-1002", username="rohan.desai@znova-demo.example", role="EMPLOYEE",
            password_hash=hash_password("LedgerForge2025!"), is_active="Y",
        )
        session.add_all([e1, e2, admin_u, emp_u])

        pr_apr = PayrollRun(run_id="PR-2025-04", period_start=date(2025, 4, 1), period_end=date(2025, 4, 30), status="PAID")
        pr_may = PayrollRun(run_id="PR-2025-05", period_start=date(2025, 5, 1), period_end=date(2025, 5, 31), status="PAID")
        session.add_all([pr_apr, pr_may])
        session.flush()

        items = [
            PayrollItem(
                payroll_item_id="PI-1", run_id="PR-2025-04", employee_id="EMP-1001",
                period_start=date(2025, 4, 1), period_end=date(2025, 4, 30),
                department_id="D-ENG", role_id="R-SWE", calendar_days=30, days_employed=30,
                payable_days=Decimal("30.00"), monthly_fixed_gross=Decimal("150000.00"),
                basic=Decimal("75000.00"), hra=Decimal("37500.00"), conveyance=Decimal("1600.00"),
                medical=Decimal("1250.00"), special_allowance=Decimal("34650.00"),
                earned_fixed_pay=Decimal("150000.00"), gross_pay=Decimal("150000.00"),
                pf_employee=Decimal("9000.00"), esi_employee=Decimal("0.00"),
                professional_tax=Decimal("200.00"), tds=Decimal("10800.00"),
                total_deductions=Decimal("20000.00"), net_pay=Decimal("130000.00"),
                pf_employer=Decimal("9000.00"), esi_employer=Decimal("0.00"),
                employer_cost=Decimal("159000.00"),
            ),
            PayrollItem(
                payroll_item_id="PI-2", run_id="PR-2025-04", employee_id="EMP-1002",
                period_start=date(2025, 4, 1), period_end=date(2025, 4, 30),
                department_id="D-FIN", role_id="R-ACC", calendar_days=30, days_employed=30,
                payable_days=Decimal("30.00"), monthly_fixed_gross=Decimal("50000.00"),
                basic=Decimal("25000.00"), hra=Decimal("12500.00"), conveyance=Decimal("1600.00"),
                medical=Decimal("1250.00"), special_allowance=Decimal("9650.00"),
                earned_fixed_pay=Decimal("50000.00"), gross_pay=Decimal("50000.00"),
                pf_employee=Decimal("3000.00"), esi_employee=Decimal("0.00"),
                professional_tax=Decimal("200.00"), tds=Decimal("1800.00"),
                total_deductions=Decimal("5000.00"), net_pay=Decimal("45000.00"),
                pf_employer=Decimal("3000.00"), esi_employer=Decimal("0.00"),
                employer_cost=Decimal("53000.00"),
            ),
            PayrollItem(
                payroll_item_id="PI-3", run_id="PR-2025-05", employee_id="EMP-1001",
                period_start=date(2025, 5, 1), period_end=date(2025, 5, 31),
                department_id="D-ENG", role_id="R-SWE", calendar_days=31, days_employed=31,
                payable_days=Decimal("31.00"), monthly_fixed_gross=Decimal("150000.00"),
                basic=Decimal("75000.00"), hra=Decimal("37500.00"), conveyance=Decimal("1600.00"),
                medical=Decimal("1250.00"), special_allowance=Decimal("34650.00"),
                earned_fixed_pay=Decimal("150000.00"), gross_pay=Decimal("150000.00"),
                pf_employee=Decimal("9000.00"), esi_employee=Decimal("0.00"),
                professional_tax=Decimal("200.00"), tds=Decimal("10800.00"),
                total_deductions=Decimal("20000.00"), net_pay=Decimal("130000.00"),
                pf_employer=Decimal("9000.00"), esi_employer=Decimal("0.00"),
                employer_cost=Decimal("159000.00"),
            ),
        ]
        session.add_all(items)
        session.commit()

    test_app = create_app()

    def _get_test_db():
        with Session(engine) as s:
            yield s

    test_app.dependency_overrides[get_db] = _get_test_db
    yield TestClient(test_app)
    test_app.dependency_overrides.clear()


def _headers(user_id: str, username: str, role: str, employee_id: str) -> dict[str, str]:
    token = create_access_token(user_id=user_id, username=username, role=role, employee_id=employee_id)
    return {"Authorization": f"Bearer {token}"}


def test_department_payroll_cost_breakdown_full(dept_report_client):
    headers = _headers("U-ADM", "admin", "ADMIN", "EMP-1001")
    resp = dept_report_client.get("/api/v1/reports/department-payroll-cost", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_type"] == "DEPARTMENT_PAYROLL_COST"
    assert data["departments_count"] == 2
    assert data["total_payroll_items"] == 3
    assert Decimal(data["company_total_gross_pay"]) == Decimal("350000.00")
    assert Decimal(data["company_total_employer_cost"]) == Decimal("371000.00")

    # Highest cost department (Engineering) must be sorted first
    first = data["departments"][0]
    assert first["department_id"] == "D-ENG"
    assert first["unique_employees"] == 1
    assert first["payroll_items_count"] == 2
    assert Decimal(first["total_employer_cost"]) == Decimal("318000.00")
    assert Decimal(first["avg_gross_per_item"]) == Decimal("150000.00")

    # Percentage shares sum to 100.00%
    share_sum = sum(Decimal(d["share_of_total_cost_percent"]) for d in data["departments"])
    assert share_sum == Decimal("100.00")


def test_department_payroll_cost_filtered_by_run_and_dates(dept_report_client):
    headers = _headers("U-ADM", "admin", "ADMIN", "EMP-1001")
    resp = dept_report_client.get(
        "/api/v1/reports/department-payroll-cost?run_id=PR-2025-04&start_date=2025-04-01&end_date=2025-04-30",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_payroll_items"] == 2
    assert Decimal(data["company_total_employer_cost"]) == Decimal("212000.00")
    # 159000 / 212000 = 75.00%, 53000 / 212000 = 25.00%
    assert Decimal(data["departments"][0]["share_of_total_cost_percent"]) == Decimal("75.00")
    assert Decimal(data["departments"][1]["share_of_total_cost_percent"]) == Decimal("25.00")


def test_department_payroll_cost_empty_range_safe(dept_report_client):
    headers = _headers("U-ADM", "admin", "ADMIN", "EMP-1001")
    resp = dept_report_client.get(
        "/api/v1/reports/department-payroll-cost?start_date=2030-01-01",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["departments_count"] == 0
    assert data["total_payroll_items"] == 0
    assert Decimal(data["company_total_employer_cost"]) == Decimal("0.00")
    assert data["departments"] == []


def test_department_payroll_cost_rbac_blocks_regular_employee(dept_report_client):
    headers = _headers("U-EMP", "rohan.desai@znova-demo.example", "EMPLOYEE", "EMP-1002")
    resp = dept_report_client.get("/api/v1/reports/department-payroll-cost", headers=headers)
    assert resp.status_code == 403
