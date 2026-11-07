"""Tests for Configurable Tax Rules (Slabs, Parameters, Statutory Rates) & Monthly Statutory Reports (Task 14 / LF-14).

Covers:
1. Annual taxable income, slab tax, Section 87A rebate, 4% cess, and / 12 monthly TDS read from database tables.
2. Only Admin can change tax slabs, tax parameters, or statutory rates (401 without token, 403 for EMPLOYEE and HR, 200 for ADMIN).
3. Changing a slab changes tax on a rerun of one month, past months are not altered, and changing the slab back restores the original tax.
4. Monthly PF, ESI, and TDS report totals equal payroll sums with 0.00 difference.
"""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import DEFAULT_DEMO_PASSWORD, hash_password
from app.db.session import get_db
from app.main import create_app
from app.models import (
    Base,
    Department,
    Employee,
    PayrollItem,
    PayrollRun,
    Role,
    SalaryComponent,
    SalaryStructure,
    StatutoryRate,
    TaxParameter,
    TaxSlab,
    User,
)


@pytest.fixture()
def tax_client():
    """Create an isolated in-memory database with tax_slabs, tax_parameters, statutory_rates,
    two payroll months (PR-2025-04 in FY2025-26 and PR-2026-09 in FY2026-27), employees, and users.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with TestingSessionLocal() as session:
        session.add(Department(department_id="D01", department_name="Engineering", cost_center="CC-101"))
        session.add(
            Role(
                role_id="R01",
                department_id="D01",
                role_title="Principal Architect",
                level=4,
                grade="G4",
                band_min_annual=200000,
                band_mid_annual=1500000,
                band_max_annual=3000000,
                overtime_eligible=False,
            )
        )

        # Seed statutory_rates
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
            session.add(
                StatutoryRate(
                    parameter=param,
                    value=Decimal(val),
                    unit=unit,
                    effective_from=eff,
                )
            )

        # Seed tax_parameters
        for param, val in [
            ("standard_deduction", "75000.00"),
            ("rebate_threshold_taxable", "1200000.00"),
            ("health_education_cess_percent", "4.00"),
        ]:
            session.add(TaxParameter(parameter=param, value=Decimal(val)))

        # Seed tax_slabs for FY2025-26 (TS-001..TS-007) and FY2026-27 (TS-008..TS-014)
        slab_defs = [
            ("0", "400000", "0"),
            ("400000", "800000", "5"),
            ("800000", "1200000", "10"),
            ("1200000", "1600000", "15"),
            ("1600000", "2000000", "20"),
            ("2000000", "2400000", "25"),
            ("2400000", None, "30"),
        ]
        for idx, (low, high, rate) in enumerate(slab_defs, start=1):
            session.add(
                TaxSlab(
                    slab_id=f"TS-{idx:03d}",
                    regime="NEW",
                    financial_year="FY2025-26",
                    income_from=Decimal(low),
                    income_to=Decimal(high) if high else None,
                    rate_percent=Decimal(rate),
                    effective_from=date(2025, 4, 1),
                )
            )
            session.add(
                TaxSlab(
                    slab_id=f"TS-{idx + 7:03d}",
                    regime="NEW",
                    financial_year="FY2026-27",
                    income_from=Decimal(low),
                    income_to=Decimal(high) if high else None,
                    rate_percent=Decimal(rate),
                    effective_from=date(2026, 4, 1),
                )
            )

        # Seed 3 employees:
        # - EMP-0006: High earner (1,50,000/mo -> 18,00,000/yr -> taxable 17,25,000 -> pays TDS & PF)
        # - EMP-0002: ESI earner (18,000/mo -> <= 21,000 -> pays ESI & PF, 0 TDS due to 87A rebate)
        # - EMP-0099 & EMP-0011: Admin & HR users
        emps = [
            ("EMP-0006", "Aarav", "Sharma", "aarav.sharma@znova-demo.example", "150000.00"),
            ("EMP-0002", "Jatin", "Jayaraman", "jatin.jayaraman@znova-demo.example", "18000.00"),
            ("EMP-0011", "Hemant", "Mathew", "hemant.mathew@znova-demo.example", "90000.00"),
            ("EMP-0099", "Sanjay", "Kumar", "sanjay.kumar@znova-demo.example", "160000.00"),
        ]
        for cid, cname in [
            ("BASIC", "Basic"),
            ("HRA", "HRA"),
            ("CONV", "Conveyance"),
            ("MED", "Medical"),
            ("SPECIAL", "Special Allowance"),
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

        for idx, (eid, fn, ln, email, mfg_str) in enumerate(emps, start=1):
            session.add(
                Employee(
                    employee_id=eid,
                    first_name=fn,
                    last_name=ln,
                    work_email=email,
                    gender="Male",
                    date_of_birth=date(1990, 5, 10),
                    hire_date=date(2023, 4, 1),
                    employment_status="Active",
                    employment_type="Permanent",
                    department_id="D01",
                    role_id="R01",
                    work_location="Bengaluru",
                    work_mode="Hybrid",
                )
            )
            mfg = Decimal(mfg_str)
            basic = (mfg * Decimal("0.40")).quantize(Decimal("0.01"))
            hra = (mfg * Decimal("0.20")).quantize(Decimal("0.01"))
            conv = Decimal("1600.00")
            med = Decimal("1250.00")
            spec = mfg - basic - hra - conv - med
            for c_idx, (cid, cname, amt) in enumerate(
                [
                    ("BASIC", "Basic", basic),
                    ("HRA", "HRA", hra),
                    ("CONV", "Conveyance", conv),
                    ("MED", "Medical", med),
                    ("SPECIAL", "Special Allowance", spec),
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
                        monthly_amount=amt,
                        effective_from=date(2023, 4, 1),
                    )
                )

        # Seed demo users
        for uid, eid, uname, urole in [
            ("U-0099", "EMP-0099", "sanjay.kumar@znova-demo.example", "ADMIN"),
            ("U-0011", "EMP-0011", "hemant.mathew@znova-demo.example", "HR"),
            ("U-0002", "EMP-0002", "jatin.jayaraman@znova-demo.example", "EMPLOYEE"),
        ]:
            session.add(
                User(
                    user_id=uid,
                    employee_id=eid,
                    username=uname,
                    role=urole,
                    password_hash=hash_password(DEFAULT_DEMO_PASSWORD, rounds=4),
                    is_active="Y",
                    mfa_enabled="N",
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
        # Process two payroll runs: PR-2025-04 (past month) and PR-2026-09 (target month)
        admin_login = client.post(
            "/api/v1/auth/login",
            json={"username": "U-0099", "password": DEFAULT_DEMO_PASSWORD},
        )
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        for m in ("2025-04", "2026-09"):
            client.post("/api/v1/payroll/runs", json={"month": m, "run_by": "EMP-0011"}, headers=admin_headers)
            client.post(f"/api/v1/payroll/runs/PR-{m}/process", json={"run_by": "EMP-0011"}, headers=admin_headers)

        yield client, TestingSessionLocal


def _token(client: TestClient, username: str) -> dict[str, str]:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": DEFAULT_DEMO_PASSWORD})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_only_admin_can_change_tax_rules(tax_client):
    """Verify no token -> 401, EMPLOYEE/HR -> 403, and ADMIN -> 200 on slab, parameter, and statutory rate updates."""
    client, _ = tax_client
    emp_h = _token(client, "U-0002")
    hr_h = _token(client, "U-0011")
    admin_h = _token(client, "U-0099")

    # 1. PATCH /api/v1/tax/slabs/TS-011
    assert client.patch("/api/v1/tax/slabs/TS-011", json={"rate_percent": "18.00"}).status_code == 401
    assert client.patch("/api/v1/tax/slabs/TS-011", json={"rate_percent": "18.00"}, headers=emp_h).status_code == 403
    assert client.patch("/api/v1/tax/slabs/TS-011", json={"rate_percent": "18.00"}, headers=hr_h).status_code == 403

    ok_resp = client.patch("/api/v1/tax/slabs/TS-011", json={"rate_percent": "15.00"}, headers=admin_h)
    assert ok_resp.status_code == 200
    assert Decimal(str(ok_resp.json()["rate_percent"])) == Decimal("15.00")

    # 2. PATCH /api/v1/tax/parameters/standard_deduction
    assert client.patch("/api/v1/tax/parameters/standard_deduction", json={"value": "75000"}).status_code == 401
    assert client.patch("/api/v1/tax/parameters/standard_deduction", json={"value": "75000"}, headers=hr_h).status_code == 403
    assert client.patch("/api/v1/tax/parameters/standard_deduction", json={"value": "75000"}, headers=admin_h).status_code == 200

    # 3. PATCH /api/v1/tax/statutory-rates/PF_WAGE_CEILING
    assert client.patch("/api/v1/tax/statutory-rates/PF_WAGE_CEILING", json={"value": "15000"}).status_code == 401
    assert client.patch("/api/v1/tax/statutory-rates/PF_WAGE_CEILING", json={"value": "15000"}, headers=emp_h).status_code == 403
    assert client.patch("/api/v1/tax/statutory-rates/PF_WAGE_CEILING", json={"value": "15000"}, headers=admin_h).status_code == 200


def test_changing_slab_changes_tax_on_rerun_and_past_months_not_altered(tax_client):
    """Change a slab (TS-011: 12L-16L in FY2026-27 from 15% to 20%), rerun one month (2026-09),
    verify tax changes for EMP-0006 and PR-2026-09, verify past month PR-2025-04 is untouched,
    and change the slab back to 15%.
    """
    client, _ = tax_client
    admin_h = _token(client, "U-0099")

    # Check EMP-0006 tax breakdown before slab change:
    # Monthly gross = 1,50,000 -> Annual gross = 18,00,000 -> Standard deduction = 75,000 -> Taxable = 17,25,000
    # Slab tax @ 15% on 12L-16L:
    #   0-4L: 0
    #   4L-8L @ 5%: 20,000
    #   8L-12L @ 10%: 40,000
    #   12L-16L @ 15%: 60,000
    #   16L-17.25L @ 20%: 25,000
    #   Raw slab tax = 1,45,000 + 4% cess (5,800) = 1,50,800/yr -> Monthly TDS = 12,566.67
    b_before = client.get("/api/v1/tax/breakdown/EMP-0006/2026-09", headers=admin_h).json()
    assert Decimal(str(b_before["annual_taxable_income"])) == Decimal("1725000.00")
    assert Decimal(str(b_before["raw_slab_tax"])) == Decimal("145000.00")
    assert Decimal(str(b_before["cess_amount"])) == Decimal("5800.00")
    assert Decimal(str(b_before["annual_total_tax"])) == Decimal("150800.00")
    assert Decimal(str(b_before["monthly_tds"])) == Decimal("12566.67")

    # Execute the slab-change rerun demo endpoint (TS-011: 15% -> 20%, rerun 2026-09, then revert)
    demo_resp = client.post(
        "/api/v1/tax/slabs/rerun-demo",
        json={
            "slab_id": "TS-011",
            "new_rate_percent": "20.00",
            "month": "2026-09",
            "employee_id": "EMP-0006",
            "revert_after_demo": True,
        },
        headers=admin_h,
    )
    assert demo_resp.status_code == 200
    data = demo_resp.json()

    # When 12L-16L slab increases from 15% to 20%, annual slab tax increases by 4,00,000 * 5% = 20,000
    # + 4% cess = +20,800/yr -> Monthly TDS increases from 12,566.67 to 14,300.00 (+1,733.33/mo)!
    emp_comp = data["employee_comparison"]
    assert Decimal(str(emp_comp["before_monthly_tds"])) == Decimal("12566.67")
    assert Decimal(str(emp_comp["after_monthly_tds"])) == Decimal("14300.00")
    assert Decimal(str(emp_comp["monthly_tds_difference"])) == Decimal("1733.33")
    assert Decimal(str(emp_comp["after_net_pay"])) == Decimal(str(emp_comp["before_net_pay"])) - Decimal("1733.33")

    # Past month (PR-2025-04) was NOT altered
    assert data["past_months_untouched_verified"] is True
    assert data["sample_past_run_id"] == "PR-2025-04"
    assert Decimal(str(data["sample_past_run_tds_before"])) == Decimal(str(data["sample_past_run_tds_after"]))

    # And after reverting back to 15%, EMP-0006's monthly TDS is back to 12,566.67
    b_restored = client.get("/api/v1/tax/breakdown/EMP-0006/2026-09", headers=admin_h).json()
    assert Decimal(str(b_restored["monthly_tds"])) == Decimal("12566.67")


def test_pf_esi_and_tds_reports_reconcile_to_payroll_sums(tax_client):
    """Verify monthly PF, ESI, and TDS reports match payroll sums with 0.00 difference."""
    client, _ = tax_client
    hr_h = _token(client, "U-0011")

    pf_rep = client.get("/api/v1/tax/reports/pf?month=2026-09", headers=hr_h)
    assert pf_rep.status_code == 200
    pf_json = pf_rep.json()
    assert pf_json["is_reconciled"] is True
    assert Decimal(str(pf_json["difference"])) == Decimal("0.00")
    assert pf_json["employees_covered"] == 4

    esi_rep = client.get("/api/v1/tax/reports/esi?month=2026-09", headers=hr_h)
    assert esi_rep.status_code == 200
    esi_json = esi_rep.json()
    assert esi_json["is_reconciled"] is True
    assert Decimal(str(esi_json["difference"])) == Decimal("0.00")
    assert esi_json["employees_covered"] == 1  # EMP-0002 (18,000 <= 21,000)

    tds_rep = client.get("/api/v1/tax/reports/tds?month=2026-09", headers=hr_h)
    assert tds_rep.status_code == 200
    tds_json = tds_rep.json()
    assert tds_json["is_reconciled"] is True
    assert Decimal(str(tds_json["difference"])) == Decimal("0.00")
    assert tds_json["employees_taxed"] == 2  # EMP-0006 and EMP-0099

    sum_rep = client.get("/api/v1/tax/reports/summary", headers=hr_h)
    assert sum_rep.status_code == 200
    sum_json = sum_rep.json()
    assert sum_json["all_reconciled"] is True
    assert Decimal(str(sum_json["max_abs_difference"])) == Decimal("0.00")
