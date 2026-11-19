"""Tests for data exports, streaming CSV endpoints, incremental delta, and OpenAPI examples (Task 19)."""

from datetime import date, datetime
from decimal import Decimal
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.main import app, create_app
from app.models.base import Base
from app.models.department import Department
from app.models.employee import Employee
from app.models.ledger import ChartOfAccount, JournalEntry, JournalLine
from app.models.payroll import PayrollItem, PayrollRun
from app.models.role import Role
from app.models.user import User


@pytest.fixture
def export_client():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        dept = Department(department_id="D-ENG", department_name="Engineering", cost_center="CC-ENG", is_active=True)
        role = Role(
            role_id="R-SWE1", department_id="D-ENG", role_title="Software Engineer",
            level=1, grade="L1", band_min_annual=100000, band_mid_annual=200000, band_max_annual=300000, is_active=True
        )
        session.add_all([dept, role])
        session.flush()

        emp = Employee(
            employee_id="EMP-0002",
            first_name="Jatin",
            last_name="Jayaraman",
            work_email="jatin.jayaraman@znova-demo.example",
            gender="Male",
            date_of_birth=date(1992, 5, 14),
            hire_date=date(2023, 1, 1),
            department_id="D-ENG",
            role_id="R-SWE1",
            employment_status="Active",
            employment_type="Permanent",
            work_location="Bengaluru",
            work_mode="Hybrid",
        )
        admin_user = User(
            user_id="U-0099",
            employee_id="EMP-0002",
            username="admin",
            role="ADMIN",
            password_hash=hash_password("LedgerForge2025!"),
            is_active="Y",
        )
        session.add_all([emp, admin_user])

        # Payroll Run & Item
        pr = PayrollRun(
            run_id="PR-2025-04",
            period_start=date(2025, 4, 1),
            period_end=date(2025, 4, 30),
            status="PAID",
        )
        pi = PayrollItem(
            payroll_item_id="PI-00001",
            run_id="PR-2025-04",
            employee_id="EMP-0002",
            period_start=date(2025, 4, 1),
            period_end=date(2025, 4, 30),
            department_id="D-ENG",
            role_id="R-SWE1",
            calendar_days=30,
            days_employed=30,
            payable_days=Decimal("30.00"),
            monthly_fixed_gross=Decimal("179130.40"),
            basic=Decimal("89565.20"),
            hra=Decimal("44782.60"),
            conveyance=Decimal("1600.00"),
            medical=Decimal("1250.00"),
            special_allowance=Decimal("41932.60"),
            earned_fixed_pay=Decimal("179130.40"),
            gross_pay=Decimal("179130.40"),
            pf_employee=Decimal("10747.82"),
            esi_employee=Decimal("0.00"),
            professional_tax=Decimal("200.00"),
            tds=Decimal("9677.97"),
            total_deductions=Decimal("20625.79"),
            net_pay=Decimal("158504.61"),
            employer_cost=Decimal("190628.22"),
        )
        session.add_all([pr, pi])

        # Ledger Entry & Lines
        coa1 = ChartOfAccount(account_code=5001, account_name="Basic Pay Expense", account_type="EXPENSE", normal_balance="DEBIT", statement="P&L", is_group="N", is_active="Y")
        coa2 = ChartOfAccount(account_code=2100, account_name="Salaries Payable", account_type="LIABILITY", normal_balance="CREDIT", statement="BALANCE_SHEET", is_group="N", is_active="Y")
        je = JournalEntry(
            entry_id="JE-000105",
            entry_date=date(2025, 4, 30),
            posting_period="2025-04",
            financial_year="FY2025-26",
            description="Payroll posting PR-2025-04",
            source_type="PAYROLL_RUN",
            source_id="PR-2025-04",
            status="POSTED",
            total_debit=Decimal("179130.40"),
            total_credit=Decimal("179130.40"),
        )
        jl1 = JournalLine(line_id="JL-0001", entry_id="JE-000105", line_no=1, account_code=5001, debit=Decimal("179130.40"), credit=Decimal("0.00"))
        jl2 = JournalLine(line_id="JL-0002", entry_id="JE-000105", line_no=2, account_code=2100, debit=Decimal("0.00"), credit=Decimal("179130.40"))
        session.add_all([coa1, coa2, je, jl1, jl2])

        session.commit()

    test_app = create_app()

    def _get_test_db():
        with Session(engine) as s:
            yield s

    test_app.dependency_overrides[get_db] = _get_test_db
    yield TestClient(test_app)
    test_app.dependency_overrides.clear()


def get_admin_headers():
    token = create_access_token(
        user_id="U-0099",
        username="admin",
        role="ADMIN",
        employee_id="EMP-0002",
    )
    return {"Authorization": f"Bearer {token}"}


def test_export_employees_streaming_csv(export_client):
    headers = get_admin_headers()
    response = export_client.get(
        "/api/v1/exports/employees?start_date=2022-01-01&end_date=2024-12-31",
        headers=headers,
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment; filename=" in response.headers["content-disposition"]
    lines = response.text.strip().split("\n")
    assert len(lines) >= 2
    assert "employee_id" in lines[0]
    assert "EMP-0002" in response.text


def test_export_payroll_items_streaming_csv(export_client):
    headers = get_admin_headers()
    response = export_client.get(
        "/api/v1/exports/payroll?run_id=PR-2025-04&start_date=2025-04-01&end_date=2025-04-30",
        headers=headers,
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    lines = response.text.strip().split("\n")
    assert len(lines) >= 2
    assert "payroll_item_id" in lines[0]
    assert "gross_pay" in lines[0]
    assert "179130.40" in response.text


def test_export_ledger_streaming_csv(export_client):
    headers = get_admin_headers()
    response = export_client.get(
        "/api/v1/exports/ledger?start_date=2025-04-01&end_date=2025-04-30",
        headers=headers,
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    lines = response.text.strip().split("\n")
    assert len(lines) >= 2
    assert "entry_id" in lines[0]
    assert "account_code" in lines[0]
    assert "5001" in response.text


def test_export_incremental_changes(export_client):
    headers = get_admin_headers()
    response = export_client.get("/api/v1/exports/changes?since=2020-01-01T00:00:00", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "changed_employees" in data
    assert "changed_journal_entries" in data
    assert data["summary"]["employees_changed"] > 0
    assert data["summary"]["journal_entries_changed"] > 0


def test_export_payroll_excel_xlsx(export_client):
    headers = get_admin_headers()
    response = export_client.get(
        "/api/v1/exports/payroll?run_id=PR-2025-04&format=xlsx",
        headers=headers,
    )
    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]
    assert ".xlsx" in response.headers["content-disposition"]
    # XLSX files are ZIP archives starting with PK\x03\x04
    assert response.content[:4] == b"PK\x03\x04"


def test_openapi_schema_has_rich_examples():
    app.openapi_schema = None
    schema = app.openapi()
    assert len(schema["paths"]) > 0
    # Check login requestBody example
    login_op = schema["paths"]["/api/v1/auth/login"]["post"]
    assert "example" in login_op["requestBody"]["content"]["application/json"]
    ex = login_op["requestBody"]["content"]["application/json"]["example"]
    assert ex["username"] in ("admin", "sanjay.kumar@znova-demo.example")

    # Assert EVERY endpoint operation has at least one example (request, param, or response)
    missing = []
    for path_str, path_item in schema["paths"].items():
        for method, op in path_item.items():
            if not isinstance(op, dict):
                continue
            has_ex = False
            rb = op.get("requestBody", {}).get("content", {}).get("application/json", {})
            if "example" in rb or "examples" in rb:
                has_ex = True
            for param in op.get("parameters", []):
                if "example" in param:
                    has_ex = True
            for resp in op.get("responses", {}).values():
                for cobj in resp.get("content", {}).values():
                    if "example" in cobj or "examples" in cobj:
                        has_ex = True
            if not has_ex:
                missing.append(f"{method.upper()} {path_str}")
    assert missing == [], f"Endpoints missing OpenAPI examples: {missing}"
