"""Security, Authentication (JWT + bcrypt), and Role-Based Access Control Tests (Task 13 / LF-13).

Covers:
1. Passwords in `users` table are hashed with bcrypt ($2b$...), never stored as plaintext, and never returned in API responses.
2. POST /api/v1/auth/login issues a 30-minute JWT signed with SECRET_KEY from environment settings.
3. No token -> 401 Unauthorized and Wrong role -> 403 Forbidden across 6 protected routes.
4. Ownership enforcement: an EMPLOYEE can read only their own payslip, profile, attendance, and leave data (403 on another employee's ID).
5. Deactivated user holding a still-unexpired JWT token is immediately rejected with 401 USER_DEACTIVATED.
"""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
import jwt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.security import (
    ALGORITHM,
    DEFAULT_DEMO_PASSWORD,
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.main import create_app
from app.models import (
    Base,
    ChartOfAccount,
    Department,
    Employee,
    LeaveBalance,
    PayrollItem,
    PayrollRun,
    Role,
    SalaryComponent,
    SalaryStructure,
    User,
)


@pytest.fixture()
def security_client():
    """Create an isolated in-memory database with demo Employees, Payroll Payslips, and Users across ADMIN, HR, and EMPLOYEE roles."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with TestingSessionLocal() as session:
        session.add(
            Department(
                department_id="D01",
                department_name="Engineering",
                cost_center="CC-101",
            )
        )
        session.add(
            ChartOfAccount(
                account_code=2001,
                account_name="Accounts Payable",
                account_type="LIABILITY",
                normal_balance="CREDIT",
                is_group="N",
                statement="BALANCE_SHEET",
                is_active="Y",
            )
        )
        session.add(
            Role(
                role_id="R01",
                department_id="D01",
                role_title="Software Engineer",
                level=2,
                grade="G2",
                band_min_annual=600000,
                band_mid_annual=800000,
                band_max_annual=1000000,
                overtime_eligible=False,
            )
        )

        # Seed demo employees matching users.csv
        demo_emps = [
            ("EMP-0099", "Sanjay", "Kumar", "sanjay.kumar@znova-demo.example", "Active"),
            ("EMP-0011", "Hemant", "Mathew", "hemant.mathew@znova-demo.example", "Active"),
            ("EMP-0002", "Jatin", "Jayaraman", "jatin.jayaraman@znova-demo.example", "Active"),
            ("EMP-0004", "Zaid", "Selvam", "zaid.selvam@znova-demo.example", "Active"),
            ("EMP-0001", "Ganesh", "Murthy", "ganesh.murthy@znova-demo.example", "Resigned"),
        ]
        for eid, fn, ln, email, status in demo_emps:
            session.add(
                Employee(
                    employee_id=eid,
                    first_name=fn,
                    last_name=ln,
                    work_email=email,
                    gender="Male",
                    date_of_birth=date(1992, 5, 14),
                    hire_date=date(2023, 4, 1),
                    employment_status=status,
                    employment_type="Permanent",
                    department_id="D01",
                    role_id="R01",
                    work_location="Bengaluru",
                    work_mode="Hybrid",
                )
            )
            session.add(
                LeaveBalance(
                    employee_id=eid,
                    as_of_date=date(2026, 9, 30),
                    financial_year="FY2026-27",
                    cl_entitlement=Decimal("12.0"),
                    cl_used=Decimal("2.0"),
                    cl_balance=Decimal("10.0"),
                    sl_entitlement=Decimal("12.0"),
                    sl_used=Decimal("1.0"),
                    sl_balance=Decimal("11.0"),
                    el_used_fy=Decimal("0.0"),
                    el_balance=Decimal("15.0"),
                    pending_days=Decimal("0.0"),
                )
            )

        # Seed salary components and salary structures for EMP-0002 and EMP-0004 so payslip engine calculates 200 OK
        for cid, cname in [
            ("COMP-01", "Basic"),
            ("COMP-02", "HRA"),
            ("COMP-03", "Conveyance"),
            ("COMP-04", "Medical"),
            ("COMP-05", "Special Allowance"),
        ]:
            session.add(
                SalaryComponent(
                    component_id=cid,
                    component_name=cname,
                    component_type="EARNING",
                    taxable="Y",
                    is_fixed="Y",
                )
            )
        for idx, eid in enumerate(["EMP-0002", "EMP-0004"], start=1):
            for c_idx, (cid, cname, amt) in enumerate(
                [
                    ("COMP-01", "Basic", "32000.00"),
                    ("COMP-02", "HRA", "16000.00"),
                    ("COMP-03", "Conveyance", "1600.00"),
                    ("COMP-04", "Medical", "1250.00"),
                    ("COMP-05", "Special Allowance", "29150.00"),
                ],
                start=1,
            ):
                session.add(
                    SalaryStructure(
                        structure_id=f"SS-{idx:02d}-{c_idx:02d}",
                        employee_id=eid,
                        component_id=cid,
                        component_name=cname,
                        component_type="EARNING",
                        monthly_amount=Decimal(amt),
                        effective_from=date(2023, 4, 1),
                    )
                )

        # Seed a payroll run and two payslips (for EMP-0002 and EMP-0004)
        session.add(
            PayrollRun(
                run_id="PR-2025-04",
                period_start=date(2025, 4, 1),
                period_end=date(2025, 4, 30),
                pay_date=date(2025, 4, 30),
                employees_paid=2,
                total_gross=Decimal("160000.00"),
                total_deductions=Decimal("20000.00"),
                total_net=Decimal("140000.00"),
                total_employer_contributions=Decimal("7200.00"),
                total_employer_cost=Decimal("167200.00"),
                status="PROCESSED",
                run_by="EMP-0011",
            )
        )
        for idx, eid in enumerate(["EMP-0002", "EMP-0004"], start=1):
            session.add(
                PayrollItem(
                    payroll_item_id=f"PI-202504-{idx:04d}",
                    run_id="PR-2025-04",
                    employee_id=eid,
                    period_start=date(2025, 4, 1),
                    period_end=date(2025, 4, 30),
                    department_id="D01",
                    role_id="R01",
                    calendar_days=30,
                    days_employed=30,
                    lop_days=Decimal("0.0"),
                    payable_days=Decimal("30.0"),
                    monthly_fixed_gross=Decimal("80000.00"),
                    basic=Decimal("32000.00"),
                    hra=Decimal("16000.00"),
                    conveyance=Decimal("1600.00"),
                    medical=Decimal("1250.00"),
                    special_allowance=Decimal("29150.00"),
                    earned_fixed_pay=Decimal("80000.00"),
                    overtime_hours_paid=Decimal("0.0"),
                    overtime_pay=Decimal("0.00"),
                    variable_pay=Decimal("0.00"),
                    gross_pay=Decimal("80000.00"),
                    pf_employee=Decimal("3600.00"),
                    esi_employee=Decimal("0.00"),
                    professional_tax=Decimal("200.00"),
                    tds=Decimal("6200.00"),
                    other_deductions=Decimal("0.00"),
                    total_deductions=Decimal("10000.00"),
                    net_pay=Decimal("70000.00"),
                    pf_employer=Decimal("3600.00"),
                    esi_employer=Decimal("0.00"),
                    employer_cost=Decimal("83600.00"),
                )
            )

        # Seed demo users with bcrypt-hashed passwords
        demo_users = [
            ("U-0099", "EMP-0099", "sanjay.kumar@znova-demo.example", "ADMIN", "Y", "Y"),
            ("U-0011", "EMP-0011", "hemant.mathew@znova-demo.example", "HR", "Y", "Y"),
            ("U-0002", "EMP-0002", "jatin.jayaraman@znova-demo.example", "EMPLOYEE", "Y", "N"),
            ("U-0004", "EMP-0004", "zaid.selvam@znova-demo.example", "EMPLOYEE", "Y", "N"),
            ("U-0001", "EMP-0001", "ganesh.murthy@znova-demo.example", "EMPLOYEE", "N", "N"),
        ]
        for uid, eid, uname, urole, active, mfa in demo_users:
            session.add(
                User(
                    user_id=uid,
                    employee_id=eid,
                    username=uname,
                    role=urole,
                    password_hash=hash_password(DEFAULT_DEMO_PASSWORD, rounds=4),
                    is_active=active,
                    mfa_enabled=mfa,
                    created_at="2023-04-01",
                    password_policy_note="Demo only — store bcrypt hash in real table",
                )
            )
        session.commit()

    app = create_app()
    app.state.enforce_auth = True

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, TestingSessionLocal


def _login_token(client: TestClient, username: str, password: str = DEFAULT_DEMO_PASSWORD) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_passwords_are_hashed_and_secret_key_from_env(security_client):
    """Verify passwords are stored as bcrypt hashes (never plaintext) and SECRET_KEY comes from settings."""
    client, SessionLocal = security_client
    settings = get_settings()
    assert settings.secret_key and len(settings.secret_key) >= 16

    with SessionLocal() as session:
        users = session.query(User).all()
        assert len(users) == 5
        for u in users:
            assert u.password_hash != DEFAULT_DEMO_PASSWORD
            assert u.password_hash.startswith("$2b$")
            assert verify_password(DEFAULT_DEMO_PASSWORD, u.password_hash) is True
            assert verify_password("WrongPassword!", u.password_hash) is False

    # Verify /auth/login returns 30-minute JWT signed with settings.secret_key
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "sanjay.kumar@znova-demo.example", "password": DEFAULT_DEMO_PASSWORD},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["expires_in"] == 1800
    assert body["role"] == "ADMIN"
    assert "password" not in str(body).lower()

    decoded = jwt.decode(body["access_token"], settings.secret_key, algorithms=[ALGORITHM])
    assert decoded["sub"] == "U-0099"
    assert decoded["role"] == "ADMIN"
    assert decoded["exp"] - decoded["iat"] == 1800

    # Wrong password -> 401
    bad_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "sanjay.kumar@znova-demo.example", "password": "wrong-password"},
    )
    assert bad_resp.status_code == 401
    assert bad_resp.json()["error_code"] == "INVALID_CREDENTIALS"


def test_no_token_401_and_wrong_role_403_across_six_routes(security_client):
    """Test at least 5 routes (here 6 routes) that:
    - No token returns 401 Unauthorized
    - Wrong role returns 403 Forbidden
    - Allowed role succeeds
    """
    client, _ = security_client
    emp_token = _login_token(client, "jatin.jayaraman@znova-demo.example")  # EMPLOYEE
    hr_token = _login_token(client, "hemant.mathew@znova-demo.example")     # HR
    admin_token = _login_token(client, "sanjay.kumar@znova-demo.example")  # ADMIN

    emp_headers = {"Authorization": f"Bearer {emp_token}"}
    hr_headers = {"Authorization": f"Bearer {hr_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Route 1: GET /api/v1/employees (Allowed: HR, ADMIN; Forbidden: EMPLOYEE)
    assert client.get("/api/v1/employees").status_code == 401
    assert client.get("/api/v1/employees", headers=emp_headers).status_code == 403
    assert client.get("/api/v1/employees", headers=hr_headers).status_code == 200

    # Route 2: POST /api/v1/payroll/runs (Allowed: HR, ADMIN; Forbidden: EMPLOYEE)
    run_payload = {
        "month": "2026-10",
        "run_id": "PR-2026-10",
        "pay_date": "2026-10-31",
        "run_by": "EMP-0011",
    }
    assert client.post("/api/v1/payroll/runs", json=run_payload).status_code == 401
    assert client.post("/api/v1/payroll/runs", json=run_payload, headers=emp_headers).status_code == 403
    assert client.post("/api/v1/payroll/runs", json=run_payload, headers=hr_headers).status_code == 201

    # Route 3: POST /api/v1/payroll/runs/{run_id}/approve (Allowed: ADMIN only; Forbidden: EMPLOYEE, HR)
    approve_payload = {"approved_by": "EMP-0099"}
    assert client.post("/api/v1/payroll/runs/PR-2025-04/approve", json=approve_payload).status_code == 401
    assert client.post("/api/v1/payroll/runs/PR-2025-04/approve", json=approve_payload, headers=emp_headers).status_code == 403
    assert client.post("/api/v1/payroll/runs/PR-2025-04/approve", json=approve_payload, headers=hr_headers).status_code == 403

    # Route 4: POST /api/v1/ledger/entries (Allowed: ADMIN only; Forbidden: EMPLOYEE, HR)
    je_payload = {
        "entry_id": "JE-TEST-9001",
        "entry_date": "2026-09-30",
        "posting_period": "2026-09",
        "financial_year": "FY2026-27",
        "description": "Security test entry",
        "source_type": "ADJUSTMENT",
        "source_id": "ADJ-9001",
        "created_by": "EMP-0099",
        "lines": [
            {"account_code": 5101, "debit": "1000.00", "credit": "0.00"},
            {"account_code": 1101, "debit": "0.00", "credit": "1000.00"},
        ],
    }
    assert client.post("/api/v1/ledger/entries", json=je_payload).status_code == 401
    assert client.post("/api/v1/ledger/entries", json=je_payload, headers=emp_headers).status_code == 403
    assert client.post("/api/v1/ledger/entries", json=je_payload, headers=hr_headers).status_code == 403

    # Route 5: GET /api/v1/expenses/report (Allowed: HR, ADMIN; Forbidden: EMPLOYEE)
    assert client.get("/api/v1/expenses/report").status_code == 401
    assert client.get("/api/v1/expenses/report", headers=emp_headers).status_code == 403
    assert client.get("/api/v1/expenses/report", headers=hr_headers).status_code == 200

    # Route 6: GET /api/v1/auth/users (Allowed: ADMIN only; Forbidden: EMPLOYEE, HR)
    assert client.get("/api/v1/auth/users").status_code == 401
    assert client.get("/api/v1/auth/users", headers=emp_headers).status_code == 403
    assert client.get("/api/v1/auth/users", headers=hr_headers).status_code == 403
    assert client.get("/api/v1/auth/users", headers=admin_headers).status_code == 200


def test_employee_can_only_read_own_payslip_and_data(security_client):
    """Verify an EMPLOYEE can read their own payslip, profile, and leave balance,
    and receives 403 Forbidden when changing the employee_id to another employee's ID.
    """
    client, _ = security_client
    emp2_token = _login_token(client, "jatin.jayaraman@znova-demo.example")  # EMP-0002
    hr_token = _login_token(client, "hemant.mathew@znova-demo.example")      # HR (EMP-0011)

    emp2_headers = {"Authorization": f"Bearer {emp2_token}"}
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    # 1. Own payslip -> 200 OK
    own_slip = client.get("/api/v1/payslips/EMP-0002/PR-2025-04", headers=emp2_headers)
    assert own_slip.status_code == 200
    assert own_slip.json()["employee_id"] == "EMP-0002"

    # 2. Another employee's payslip (EMP-0004) -> 403 Forbidden (OWNERSHIP_VIOLATION)
    other_slip = client.get("/api/v1/payslips/EMP-0004/PR-2025-04", headers=emp2_headers)
    assert other_slip.status_code == 403
    assert other_slip.json()["error_code"] == "OWNERSHIP_VIOLATION"

    # 3. HR can read any employee's payslip -> 200 OK
    hr_slip = client.get("/api/v1/payslips/EMP-0004/PR-2025-04", headers=hr_headers)
    assert hr_slip.status_code == 200

    # 4. Own employee profile & leave balance -> 200 OK, another employee's -> 403 Forbidden
    assert client.get("/api/v1/employees/EMP-0002", headers=emp2_headers).status_code == 200
    assert client.get("/api/v1/employees/EMP-0004", headers=emp2_headers).status_code == 403
    assert client.get("/api/v1/leave/balances/EMP-0002", headers=emp2_headers).status_code == 200
    assert client.get("/api/v1/leave/balances/EMP-0004", headers=emp2_headers).status_code == 403


def test_deactivated_user_holding_valid_token_is_immediately_rejected(security_client):
    """Think for yourself: What happens when a user is deactivated while holding a valid token?
    - U-0004 (EMP-0004) logs in and receives a valid 30-minute JWT.
    - While that JWT is still unexpired, ADMIN deactivates U-0004.
    - U-0004's next request using the valid JWT is immediately rejected with 401 USER_DEACTIVATED.
    - Also verify an already-inactive user (U-0001) cannot log in at all (401 USER_DEACTIVATED).
    """
    client, _ = security_client

    # Inactive user U-0001 cannot log in
    inactive_login = client.post(
        "/api/v1/auth/login",
        json={"username": "ganesh.murthy@znova-demo.example", "password": DEFAULT_DEMO_PASSWORD},
    )
    assert inactive_login.status_code == 401
    assert inactive_login.json()["error_code"] == "USER_DEACTIVATED"

    # Active user U-0004 logs in and gets a valid token
    u4_token = _login_token(client, "zaid.selvam@znova-demo.example")
    u4_headers = {"Authorization": f"Bearer {u4_token}"}

    # Token works before deactivation
    me_before = client.get("/api/v1/auth/me", headers=u4_headers)
    assert me_before.status_code == 200
    assert me_before.json()["user_id"] == "U-0004"

    # Admin deactivates U-0004 while U-0004 still holds the valid token
    admin_token = _login_token(client, "sanjay.kumar@znova-demo.example")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    deact_resp = client.patch("/api/v1/auth/users/U-0004/deactivate", headers=admin_headers)
    assert deact_resp.status_code == 200
    assert deact_resp.json()["is_active"] == "N"

    # U-0004 tries to use the same unexpired token -> immediately gets 401 USER_DEACTIVATED
    me_after = client.get("/api/v1/auth/me", headers=u4_headers)
    assert me_after.status_code == 401
    assert me_after.json()["error_code"] == "USER_DEACTIVATED"

    payslip_after = client.get("/api/v1/payslips/EMP-0004/PR-2025-04", headers=u4_headers)
    assert payslip_after.status_code == 401
    assert payslip_after.json()["error_code"] == "USER_DEACTIVATED"


def test_expired_token_returns_401(security_client):
    """Verify an expired JWT returns 401 TOKEN_EXPIRED."""
    client, _ = security_client
    expired_token = create_access_token(
        user_id="U-0099",
        username="sanjay.kumar@znova-demo.example",
        role="ADMIN",
        employee_id="EMP-0099",
        expires_delta=timedelta(minutes=-5),
    )
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert resp.json()["error_code"] == "TOKEN_EXPIRED"
