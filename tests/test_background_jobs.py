"""Automated test suite for Background Jobs & Queues (Task 16)."""

from datetime import date
from decimal import Decimal
import time
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
from app.models.ledger import ChartOfAccount
from app.models.payroll import StatutoryRate, TaxParameter, TaxSlab
from app.models.role import Role
from app.models.salary import SalaryComponent, SalaryStructure
from app.models.user import User


@pytest.fixture
def jobs_client():
    """Create test client with seeded Admin, Employee, Accounts, Slabs, and Salary Structures."""
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # 1. Dept & Role
        dept = Department(department_id="D01", department_name="Engineering", cost_center="CC-ENG", is_active=True)
        role = Role(
            role_id="R001",
            department_id="D01",
            role_title="Software Engineer",
            level=1,
            grade="L1",
            band_min_annual=100000,
            band_mid_annual=200000,
            band_max_annual=300000,
            is_active=True,
        )
        session.add_all([dept, role])

        # 2. Employees
        emp_admin = Employee(
            employee_id="EMP-0099",
            first_name="Sanjay",
            last_name="Kumar",
            work_email="sanjay.kumar@test.example",
            gender="Male",
            date_of_birth=date(1985, 5, 20),
            hire_date=date(2020, 1, 1),
            employment_status="Active",
            employment_type="Permanent",
            work_location="Bangalore",
            work_mode="Hybrid",
            department_id="D01",
            role_id="R001",
            is_active=True,
        )
        emp_worker = Employee(
            employee_id="EMP-0001",
            first_name="John",
            last_name="Doe",
            work_email="john.doe@test.example",
            gender="Male",
            date_of_birth=date(1992, 8, 15),
            hire_date=date(2021, 1, 1),
            employment_status="Active",
            employment_type="Permanent",
            work_location="Bangalore",
            work_mode="Hybrid",
            department_id="D01",
            role_id="R001",
            is_active=True,
        )
        emp_admin2 = Employee(
            employee_id="EMP-0731",
            first_name="Priya",
            last_name="Sharma",
            work_email="priya.sharma@test.example",
            gender="Female",
            date_of_birth=date(1988, 3, 10),
            hire_date=date(2020, 2, 1),
            employment_status="Active",
            employment_type="Permanent",
            work_location="Bangalore",
            work_mode="Hybrid",
            department_id="D01",
            role_id="R001",
            is_active=True,
        )
        session.add_all([emp_admin, emp_admin2, emp_worker])

        # 3. Users (2 ADMIN, 1 EMPLOYEE)
        u_admin = User(
            user_id="U-0099",
            employee_id="EMP-0099",
            username="sanjay.kumar@test.example",
            role="ADMIN",
            password_hash=hash_password("adminpass123"),
            is_active="Y",
            mfa_enabled="N",
        )
        u_admin2 = User(
            user_id="U-0731",
            employee_id="EMP-0731",
            username="priya.sharma@test.example",
            role="ADMIN",
            password_hash=hash_password("admin2pass123"),
            is_active="Y",
            mfa_enabled="N",
        )
        u_emp = User(
            user_id="U-0001",
            employee_id="EMP-0001",
            username="john.doe@test.example",
            role="EMPLOYEE",
            password_hash=hash_password("emppass123"),
            is_active="Y",
            mfa_enabled="N",
        )
        session.add_all([u_admin, u_admin2, u_emp])

        # 4. Chart of Accounts (for payroll ledger posting)
        coas = [
            ChartOfAccount(account_code=5001, account_name="Salaries & Wages", account_type="EXPENSE", normal_balance="DEBIT", statement="Income Statement", is_active="Y"),
            ChartOfAccount(account_code=5002, account_name="Overtime Expense", account_type="EXPENSE", normal_balance="DEBIT", statement="Income Statement", is_active="Y"),
            ChartOfAccount(account_code=5003, account_name="Bonus Expense", account_type="EXPENSE", normal_balance="DEBIT", statement="Income Statement", is_active="Y"),
            ChartOfAccount(account_code=5004, account_name="Employer PF", account_type="EXPENSE", normal_balance="DEBIT", statement="Income Statement", is_active="Y"),
            ChartOfAccount(account_code=5005, account_name="Employer ESI", account_type="EXPENSE", normal_balance="DEBIT", statement="Income Statement", is_active="Y"),
            ChartOfAccount(account_code=2100, account_name="Salaries Payable", account_type="LIABILITY", normal_balance="CREDIT", statement="Balance Sheet", is_active="Y"),
            ChartOfAccount(account_code=2110, account_name="PF Payable", account_type="LIABILITY", normal_balance="CREDIT", statement="Balance Sheet", is_active="Y"),
            ChartOfAccount(account_code=2120, account_name="ESI Payable", account_type="LIABILITY", normal_balance="CREDIT", statement="Balance Sheet", is_active="Y"),
            ChartOfAccount(account_code=2130, account_name="TDS Payable", account_type="LIABILITY", normal_balance="CREDIT", statement="Balance Sheet", is_active="Y"),
            ChartOfAccount(account_code=2140, account_name="PT Payable", account_type="LIABILITY", normal_balance="CREDIT", statement="Balance Sheet", is_active="Y"),
            ChartOfAccount(account_code=1300, account_name="Staff Advances", account_type="ASSET", normal_balance="DEBIT", statement="Balance Sheet", is_active="Y"),
            ChartOfAccount(account_code=1001, account_name="Operating Bank", account_type="ASSET", normal_balance="DEBIT", statement="Balance Sheet", is_active="Y"),
        ]
        session.add_all(coas)

        # 5. Salary Components & Structures
        sc_basic = SalaryComponent(component_id="BASIC", component_name="Basic Pay", component_type="EARNING", is_fixed="Y")
        sc_hra = SalaryComponent(component_id="HRA", component_name="House Rent Allowance", component_type="EARNING", is_fixed="Y")
        sc_spec = SalaryComponent(component_id="SPECIAL", component_name="Special Allowance", component_type="EARNING", is_fixed="Y")
        session.add_all([sc_basic, sc_hra, sc_spec])
        session.flush()

        structures = [
            SalaryStructure(structure_id="SS-001", employee_id="EMP-0099", component_id="BASIC", component_name="Basic Pay", component_type="EARNING", monthly_amount=Decimal("30000.00"), effective_from=date(2020, 1, 1)),
            SalaryStructure(structure_id="SS-002", employee_id="EMP-0099", component_id="HRA", component_name="HRA", component_type="EARNING", monthly_amount=Decimal("15000.00"), effective_from=date(2020, 1, 1)),
            SalaryStructure(structure_id="SS-003", employee_id="EMP-0099", component_id="SPECIAL", component_name="Special", component_type="EARNING", monthly_amount=Decimal("5000.00"), effective_from=date(2020, 1, 1)),
            SalaryStructure(structure_id="SS-004", employee_id="EMP-0001", component_id="BASIC", component_name="Basic Pay", component_type="EARNING", monthly_amount=Decimal("20000.00"), effective_from=date(2021, 1, 1)),
            SalaryStructure(structure_id="SS-005", employee_id="EMP-0001", component_id="HRA", component_name="HRA", component_type="EARNING", monthly_amount=Decimal("10000.00"), effective_from=date(2021, 1, 1)),
        ]
        session.add_all(structures)

        # 6. Statutory Rates
        stat_rows = [
            ("PF_EMPLOYEE_RATE", "12.0", "percent of basic", date(2025, 4, 1)),
            ("PF_EMPLOYER_RATE", "12.0", "percent of basic", date(2025, 4, 1)),
            ("PF_WAGE_CEILING", "15000.0", "INR per month", date(2025, 4, 1)),
            ("ESI_EMPLOYEE_RATE", "0.75", "percent of gross", date(2025, 4, 1)),
            ("ESI_EMPLOYER_RATE", "3.25", "percent of gross", date(2025, 4, 1)),
            ("ESI_WAGE_LIMIT", "21000.0", "INR per month", date(2025, 4, 1)),
            ("PT_MONTHLY", "200.0", "INR per month", date(2025, 4, 1)),
            ("PT_GROSS_THRESHOLD", "25000.0", "INR per month", date(2025, 4, 1)),
            ("OT_MULTIPLIER", "2.0", "x hourly rate", date(2025, 4, 1)),
            ("OT_MONTHLY_CAP_HOURS", "50.0", "hours", date(2025, 4, 1)),
            ("WORKING_HOURS_PER_MONTH", "208.0", "hours", date(2025, 4, 1)),
        ]
        for param, val, unit, eff in stat_rows:
            session.add(StatutoryRate(parameter=param, value=Decimal(val), unit=unit, effective_from=eff))

        # 7. Tax Parameters
        for param, val in [
            ("standard_deduction", "75000.00"),
            ("rebate_threshold_taxable", "1200000.00"),
            ("health_education_cess_percent", "4.00"),
        ]:
            session.add(TaxParameter(parameter=param, value=Decimal(val)))

        # 8. Tax Slabs for FY2026-27
        slab_defs = [
            ("0", "400000", "0"),
            ("400000", "800000", "5"),
            ("800000", "1200000", "10"),
            ("1200000", "1600000", "15"),
            ("1600000", None, "20"),
        ]
        for idx, (low, high, rate) in enumerate(slab_defs, start=1):
            session.add(
                TaxSlab(
                    slab_id=f"TS-{idx:03d}",
                    regime="NEW",
                    financial_year="FY2026-27",
                    income_from=Decimal(low),
                    income_to=Decimal(high) if high else None,
                    rate_percent=Decimal(rate),
                    effective_from=date(2026, 4, 1),
                )
            )

        session.commit()

    test_app = create_app()

    def _override_get_db():
        with Session(engine) as s:
            yield s

    test_app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(test_app)
    test_app.dependency_overrides.clear()
    engine.dispose()


def test_bulk_payroll_job_unauthorized(jobs_client: TestClient):
    """Calling bulk run without a token must return 401."""
    res = jobs_client.post("/api/v1/jobs/payroll/bulk-run")
    assert res.status_code == 401
    assert res.json().get("error_code") == "MISSING_TOKEN"


def test_bulk_payroll_job_employee_forbidden(jobs_client: TestClient):
    """An EMPLOYEE role cannot trigger bulk payroll runs (403 Forbidden)."""
    token = create_access_token(
        user_id="U-0001",
        username="john.doe@test.example",
        role="EMPLOYEE",
        employee_id="EMP-0001",
    )
    headers = {"Authorization": f"Bearer {token}"}
    res = jobs_client.post("/api/v1/jobs/payroll/bulk-run", headers=headers)
    assert res.status_code == 403
    assert res.json().get("error_code") in ("INSUFFICIENT_ROLE", "FORBIDDEN")


def test_trigger_and_poll_bulk_payroll_job(jobs_client: TestClient):
    """ADMIN enqueues a bulk payroll job for 2 months, polls progress, and verifies completion."""
    token = create_access_token(
        user_id="U-0099",
        username="sanjay.kumar@test.example",
        role="ADMIN",
        employee_id="EMP-0099",
    )
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "start_month": "2026-08",
        "end_month": "2026-09",
        "auto_approve": True,
        "allow_rerun": True,
        "run_by": "U-0099",
    }
    create_res = jobs_client.post("/api/v1/jobs/payroll/bulk-run", json=payload, headers=headers)
    assert create_res.status_code == 202
    data = create_res.json()
    assert "job_id" in data
    assert data["status"] in ("PENDING", "RUNNING", "COMPLETED")
    assert data["total_items"] == 2
    job_id = data["job_id"]

    # Poll for progress/completion
    completed = False
    final_data = {}
    for _ in range(40):
        poll_res = jobs_client.get(f"/api/v1/jobs/payroll/{job_id}", headers=headers)
        assert poll_res.status_code == 200
        poll_data = poll_res.json()
        if poll_data["status"] == "COMPLETED":
            completed = True
            final_data = poll_data
            break
        elif poll_data["status"] == "FAILED":
            pytest.fail(f"Job failed: {poll_data.get('error_message')}")
        time.sleep(0.3)

    assert completed is True
    assert final_data["progress_percent"] == 100.0
    assert final_data["processed_items"] == 2
    assert final_data["results"] is not None
    assert len(final_data["results"]) == 2


def test_get_nonexistent_job_404(jobs_client: TestClient):
    """Polling a nonexistent job must return 404."""
    token = create_access_token(
        user_id="U-0099",
        username="sanjay.kumar@test.example",
        role="ADMIN",
        employee_id="EMP-0099",
    )
    headers = {"Authorization": f"Bearer {token}"}
    res = jobs_client.get("/api/v1/jobs/payroll/job_invalid_99999", headers=headers)
    assert res.status_code == 404
    assert "not found" in res.json().get("detail", "").lower()


def test_list_background_jobs(jobs_client: TestClient):
    """ADMIN can retrieve the list of recent background jobs."""
    token = create_access_token(
        user_id="U-0099",
        username="sanjay.kumar@test.example",
        role="ADMIN",
        employee_id="EMP-0099",
    )
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"start_month": "2026-09", "end_month": "2026-09", "auto_approve": False}
    jobs_client.post("/api/v1/jobs/payroll/bulk-run", json=payload, headers=headers)

    res = jobs_client.get("/api/v1/jobs", headers=headers)
    assert res.status_code == 200
    jobs = res.json()
    assert isinstance(jobs, list)
    assert len(jobs) >= 1
    assert "job_id" in jobs[0]
    assert "status" in jobs[0]
