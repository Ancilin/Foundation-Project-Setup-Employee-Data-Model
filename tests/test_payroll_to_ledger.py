"""Tests for Task 12 (LF-12): Payroll Run Status Flow (DRAFT -> PROCESSED -> APPROVED -> PAID),
Task 7 Engine Integration, Idempotent Auto-Posting to Ledger (Double-Click Protection),
Atomic Savepoint Rollback on Mid-Flight Failure, 18-Month Check 2 Reconciliation, and Run Reversal.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
import pandas as pd
import pytest
from sqlalchemy import create_engine, func, insert, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import (
    Attendance,
    Base,
    ChartOfAccount,
    Department,
    Employee,
    JournalEntry,
    JournalLine,
    PayrollItem,
    PayrollRun,
    Role,
    SalaryComponent,
    SalaryStructure,
    TaxSlab,
)
from app.services.ledger_service import post_payroll_run_to_ledger, round_money
from app.services.payroll_service import approve_payroll_run

ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = ROOT / "data" / "csv"


@pytest.fixture(scope="module")
def payroll_ledger_client():
    """Create an isolated in-memory database seeded with all 18 payroll runs, 7,340 payroll items,
    chart_of_accounts, and a sample of employees/roles/salary_structures for new-run processing tests.
    Posts all 18 payroll runs via post_payroll_run_to_ledger().
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as session:
        # 1. Chart of Accounts
        df_coa = pd.read_csv(CSV_DIR / "chart_of_accounts.csv")
        for _, r in df_coa.iterrows():
            pcode = int(float(r["parent_code"])) if pd.notna(r.get("parent_code")) else None
            session.add(
                ChartOfAccount(
                    account_code=int(r["account_code"]),
                    account_name=str(r["account_name"]).strip(),
                    account_type=str(r["account_type"]).strip(),
                    normal_balance=str(r["normal_balance"]).strip(),
                    parent_code=pcode,
                    is_group=str(r["is_group"]).strip(),
                    statement=str(r["statement"]).strip(),
                    is_active=str(r["is_active"]).strip(),
                )
            )

        # 2. Departments & Roles
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

        df_roles = pd.read_csv(CSV_DIR / "roles.csv")
        for _, r in df_roles.iterrows():
            session.add(
                Role(
                    role_id=str(r["role_id"]).strip(),
                    department_id=str(r["department_id"]).strip(),
                    role_title=str(r["role_title"]).strip(),
                    level=str(r["level"]).strip(),
                    grade=str(r["grade"]).strip(),
                    band_min_annual=Decimal(str(r["band_min_annual"])),
                    band_mid_annual=Decimal(str(r["band_mid_annual"])),
                    band_max_annual=Decimal(str(r["band_max_annual"])),
                    overtime_eligible=str(r["overtime_eligible"]).strip().upper() == "Y",
                )
            )

        # 3. Employees (all 745 so foreign keys on PayrollItem succeed)
        df_emp = pd.read_csv(CSV_DIR / "employees.csv")
        emp_records = []
        for r in df_emp.to_dict(orient="records"):
            emp_records.append(
                {
                    "employee_id": str(r["employee_id"]).strip(),
                    "first_name": str(r["first_name"]).strip(),
                    "last_name": str(r["last_name"]).strip(),
                    "work_email": str(r["work_email"]).strip(),
                    "gender": str(r["gender"]).strip(),
                    "date_of_birth": date.fromisoformat(str(r["date_of_birth"])[:10]),
                    "hire_date": date.fromisoformat(str(r["hire_date"])[:10]),
                    "exit_date": date.fromisoformat(str(r["exit_date"])[:10])
                    if pd.notna(r.get("exit_date")) and str(r.get("exit_date")).strip() != ""
                    else None,
                    "employment_status": str(r["employment_status"]).strip(),
                    "employment_type": str(r["employment_type"]).strip(),
                    "department_id": str(r["department_id"]).strip(),
                    "role_id": str(r["role_id"]).strip(),
                    "manager_id": str(r["manager_id"]).strip()
                    if pd.notna(r.get("manager_id")) and str(r.get("manager_id")).strip() != ""
                    else None,
                    "work_location": str(r["work_location"]).strip(),
                    "work_mode": str(r["work_mode"]).strip(),
                    "is_active": str(r["employment_status"]).strip() == "Active",
                }
            )
        session.execute(insert(Employee), emp_records)

        # 4. Tax Slabs & Salary Components + Structures for first 5 active employees (for fast 2026-10 process test)
        df_slabs = pd.read_csv(CSV_DIR / "tax_slabs.csv")
        for _, r in df_slabs.iterrows():
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

        df_sc = pd.read_csv(CSV_DIR / "salary_components.csv")
        for _, r in df_sc.iterrows():
            session.add(
                SalaryComponent(
                    component_id=str(r["component_id"]).strip(),
                    component_name=str(r["component_name"]).strip(),
                    component_type=str(r["component_type"]).strip(),
                    taxable=str(r["taxable"]).strip(),
                    calculation_rule=str(r["calculation_rule"]).strip(),
                    is_fixed=str(r["is_fixed"]).strip(),
                )
            )

        sample_emp_ids = {"EMP-0001", "EMP-0002", "EMP-0003", "EMP-0004", "EMP-0005"}
        df_ss = pd.read_csv(CSV_DIR / "salary_structures.csv")
        df_ss = df_ss[df_ss["employee_id"].isin(sample_emp_ids)]
        for _, r in df_ss.iterrows():
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
                    if pd.notna(r.get("effective_to")) and str(r.get("effective_to")).strip() != ""
                    else None,
                    revision_id=str(r["revision_id"]).strip(),
                )
            )

        # 5. Payroll Runs (all 18 months) & Payroll Items (all 7,340 rows)
        df_pr = pd.read_csv(CSV_DIR / "payroll_runs.csv")
        for _, r in df_pr.iterrows():
            session.add(
                PayrollRun(
                    run_id=str(r["run_id"]).strip(),
                    period_start=date.fromisoformat(str(r["period_start"])[:10]),
                    period_end=date.fromisoformat(str(r["period_end"])[:10]),
                    pay_date=date.fromisoformat(str(r["pay_date"])[:10])
                    if pd.notna(r.get("pay_date")) and str(r.get("pay_date")).strip() != ""
                    else None,
                    employees_paid=int(r["employees_paid"]),
                    total_gross=Decimal(str(r["total_gross"])),
                    total_deductions=Decimal(str(r["total_deductions"])),
                    total_net=Decimal(str(r["total_net"])),
                    total_employer_contributions=Decimal(str(r["total_employer_contributions"])),
                    total_employer_cost=Decimal(str(r["total_employer_cost"])),
                    status=str(r["status"]).strip(),
                    run_by=str(r["run_by"]).strip() if pd.notna(r.get("run_by")) else None,
                    approved_by=str(r["approved_by"]).strip() if pd.notna(r.get("approved_by")) else None,
                    approved_at=str(r["approved_at"]).strip() if pd.notna(r.get("approved_at")) else None,
                    idempotency_key=str(r["idempotency_key"]).strip()
                    if pd.notna(r.get("idempotency_key"))
                    else None,
                    journal_entry_id=str(r["journal_entry_id"]).strip()
                    if pd.notna(r.get("journal_entry_id"))
                    else None,
                    calculation_version=str(r["calculation_version"]).strip()
                    if pd.notna(r.get("calculation_version"))
                    else None,
                )
            )

        df_pi = pd.read_csv(CSV_DIR / "payroll_items.csv")
        pi_records = []
        for idx, r in enumerate(df_pi.to_dict(orient="records"), start=1):
            pi_records.append(
                {
                    "payroll_item_id": str(r.get("payroll_item_id") or f"PI-{idx:06d}"),
                    "run_id": str(r["run_id"]).strip(),
                    "employee_id": str(r["employee_id"]).strip(),
                    "period_start": date.fromisoformat(str(r["period_start"])[:10]),
                    "period_end": date.fromisoformat(str(r["period_end"])[:10]),
                    "department_id": str(r["department_id"]).strip(),
                    "role_id": str(r["role_id"]).strip(),
                    "calendar_days": int(r["calendar_days"]),
                    "days_employed": int(r["days_employed"]),
                    "lop_days": Decimal(str(r["lop_days"])),
                    "payable_days": Decimal(str(r["payable_days"])),
                    "monthly_fixed_gross": Decimal(str(r["monthly_fixed_gross"])),
                    "basic": Decimal(str(r["basic"])),
                    "hra": Decimal(str(r["hra"])),
                    "conveyance": Decimal(str(r["conveyance"])),
                    "medical": Decimal(str(r["medical"])),
                    "special_allowance": Decimal(str(r["special_allowance"])),
                    "earned_fixed_pay": Decimal(str(r["earned_fixed_pay"])),
                    "overtime_hours_paid": Decimal(str(r["overtime_hours_paid"])),
                    "overtime_pay": Decimal(str(r["overtime_pay"])),
                    "variable_pay": Decimal(str(r["variable_pay"])),
                    "variable_pay_type": str(r["variable_pay_type"]).strip()
                    if pd.notna(r.get("variable_pay_type"))
                    else None,
                    "gross_pay": Decimal(str(r["gross_pay"])),
                    "pf_employee": Decimal(str(r["pf_employee"])),
                    "esi_employee": Decimal(str(r["esi_employee"])),
                    "professional_tax": Decimal(str(r["professional_tax"])),
                    "tds": Decimal(str(r["tds"])),
                    "other_deductions": Decimal(str(r["other_deductions"])),
                    "total_deductions": Decimal(str(r["total_deductions"])),
                    "net_pay": Decimal(str(r["net_pay"])),
                    "pf_employer": Decimal(str(r["pf_employer"])),
                    "esi_employer": Decimal(str(r["esi_employer"])),
                    "employer_cost": Decimal(str(r["employer_cost"])),
                    "calculation_note": str(r["calculation_note"]).strip()
                    if pd.notna(r.get("calculation_note"))
                    else None,
                }
            )
        session.execute(insert(PayrollItem), pi_records)
        session.commit()

        # 6. Post all 18 payroll runs to the ledger via our own engine!
        for _, r in df_pr.iterrows():
            rid = str(r["run_id"]).strip()
            je_id = str(r["journal_entry_id"]).strip()
            post_payroll_run_to_ledger(session, rid, entry_id=je_id)

    def override_get_db():
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c, TestingSessionLocal
    app.dependency_overrides.clear()
    engine.dispose()


def test_all_18_months_check_2_reconciliation_and_run_journal_links(payroll_ledger_client):
    """Verify Check 2 passes across all 18 months with 0.00 difference and each run points to its journal_entry_id."""
    client, _ = payroll_ledger_client

    resp = client.get("/payroll/runs/reconciliation")
    assert resp.status_code == 200
    rep = resp.json()

    assert rep["total_runs"] == 18
    assert rep["all_months_match"] is True
    assert Decimal(rep["largest_monthly_difference"]) == Decimal("0.00")
    assert Decimal(rep["total_run_employer_cost"]) == Decimal("861586392.42")
    assert Decimal(rep["total_ledger_employer_cost"]) == Decimal("861586392.42")

    for r in rep["runs"]:
        assert r["matches"] is True
        assert Decimal(r["difference"]) == Decimal("0.00")
        assert r["journal_entry_id"] is not None and r["journal_entry_id"].startswith("JE-")
        assert r["idempotency_key"] == f"payroll:{r['month']}:ZNT"

    # Also inspect one specific run (PR-2025-04 -> JE-000105)
    resp_detail = client.get("/payroll/runs/PR-2025-04")
    assert resp_detail.status_code == 200
    d = resp_detail.json()
    assert d["run_id"] == "PR-2025-04"
    assert d["journal_entry_id"] == "JE-000105"
    assert Decimal(d["total_employer_cost"]) == Decimal("53363392.08")
    assert Decimal(d["ledger_employer_cost_5001_5005"]) == Decimal("53363392.08")
    assert Decimal(d["employer_cost_difference"]) == Decimal("0.00")
    assert d["journal_entry"]["entry_id"] == "JE-000105"
    assert Decimal(str(d["journal_entry"]["total_debit"])) == Decimal("53363392.08")
    assert Decimal(str(d["journal_entry"]["total_credit"])) == Decimal("53363392.08")


def test_payroll_run_lifecycle_idempotency_double_click_and_atomic_rollback(payroll_ledger_client):
    """Test:
    1) Create DRAFT run -> cannot approve or pay before processing.
    2) Process run -> calls Task 7 engine, computes totals, sets status = PROCESSED.
    3) Separation of duties -> run_by cannot approve their own run.
    4) Mid-flight ledger failure -> rolls back atomically so run stays PROCESSED with journal_entry_id=None.
    5) Approve run -> posts ONE journal entry and stores journal_entry_id on the run.
    6) Double-click / running a month twice -> posts only once (idempotent_replay=True).
    7) Pay run -> posts SALARY_PAYMENT and sets status = PAID.
    """
    client, SessionLocal = payroll_ledger_client

    # 1. Create a DRAFT payroll run for 2026-10
    resp_create = client.post(
        "/payroll/runs",
        json={"month": "2026-10", "run_by": "U-0237"},
    )
    assert resp_create.status_code == 201
    draft_run = resp_create.json()
    assert draft_run["run_id"] == "PR-2026-10"
    assert draft_run["status"] == "DRAFT"
    assert draft_run["idempotency_key"] == "payroll:2026-10:ZNT"
    assert draft_run["journal_entry_id"] is None

    # Idempotent run creation: calling POST /payroll/runs again for 2026-10 returns the same run
    resp_create_again = client.post(
        "/payroll/runs",
        json={"month": "2026-10", "run_by": "U-0237"},
    )
    assert resp_create_again.status_code == 201
    assert resp_create_again.json()["run_id"] == "PR-2026-10"

    # Guard: cannot approve or pay a DRAFT run before processing
    resp_approve_early = client.post("/payroll/runs/PR-2026-10/approve", json={"approved_by": "U-0099"})
    assert resp_approve_early.status_code == 422
    assert resp_approve_early.json()["error_code"] == "RUN_NOT_PROCESSED"

    resp_pay_early = client.post("/payroll/runs/PR-2026-10/pay", json={"paid_by": "U-0099"})
    assert resp_pay_early.status_code == 422
    assert resp_pay_early.json()["error_code"] == "RUN_NOT_APPROVED"

    # 2. Process the payroll run (calls Task 7 engine for eligible employees)
    resp_proc = client.post("/payroll/runs/PR-2026-10/process", json={"run_by": "U-0237"})
    assert resp_proc.status_code == 200
    proc_run = resp_proc.json()
    assert proc_run["status"] == "PROCESSED"
    assert proc_run["employees_paid"] >= 2
    assert Decimal(proc_run["total_employer_cost"]) > Decimal("0.00")
    assert proc_run["journal_entry_id"] is None

    # 3. Separation of duties: U-0237 ran the payroll and cannot approve it
    resp_self_app = client.post("/payroll/runs/PR-2026-10/approve", json={"approved_by": "U-0237"})
    assert resp_self_app.status_code == 422
    assert resp_self_app.json()["error_code"] == "SEPARATION_OF_DUTIES_VIOLATION"

    # 4. Atomic rollback rule when ledger posting fails halfway through
    with SessionLocal() as db:
        je_count_before = db.scalar(select(func.count(JournalEntry.entry_id)))
        with pytest.raises(RuntimeError, match="Simulated mid-flight ledger failure"):
            approve_payroll_run(
                session=db,
                run_id="PR-2026-10",
                approved_by="U-0099",
                simulate_ledger_failure=True,
            )
        je_count_after = db.scalar(select(func.count(JournalEntry.entry_id)))
        assert je_count_after == je_count_before
        pr_check = db.get(PayrollRun, "PR-2026-10")
        assert pr_check.status == "PROCESSED"
        assert pr_check.journal_entry_id is None
        assert pr_check.approved_by is None

    # 5. Approve the payroll run (first click) -> posts ONE journal entry
    resp_app1 = client.post("/payroll/runs/PR-2026-10/approve", json={"approved_by": "U-0099"})
    assert resp_app1.status_code == 200
    app1 = resp_app1.json()
    assert app1["status"] == "APPROVED"
    assert app1["approved_by"] == "U-0099"
    assert app1["idempotent_replay"] is False
    first_je_id = app1["journal_entry_id"]
    assert first_je_id is not None
    assert Decimal(app1["employer_cost_difference"]) == Decimal("0.00")

    # 6. Double-click test: approving the same run a second time posts ONLY ONCE!
    resp_app2 = client.post("/payroll/runs/PR-2026-10/approve", json={"approved_by": "U-0099"})
    assert resp_app2.status_code == 200
    app2 = resp_app2.json()
    assert app2["idempotent_replay"] is True
    assert app2["journal_entry_id"] == first_je_id

    with SessionLocal() as db:
        entries_for_run = list(
            db.scalars(
                select(JournalEntry).where(
                    JournalEntry.source_type == "PAYROLL_RUN",
                    JournalEntry.source_id == "PR-2026-10",
                )
            ).all()
        )
        assert len(entries_for_run) == 1

    # 7. Pay the approved payroll run
    resp_pay = client.post(
        "/payroll/runs/PR-2026-10/pay",
        json={"pay_date": "2026-11-01", "paid_by": "U-0099"},
    )
    assert resp_pay.status_code == 200
    paid_run = resp_pay.json()
    assert paid_run["status"] == "PAID"
    assert paid_run["pay_date"] == "2026-11-01"


def test_payroll_run_reversal_cancels_run_and_ledger_entry(payroll_ledger_client):
    """Test the Challenge: reversing a posted payroll run marks it REVERSED and posts
    a reversing journal entry that cancels out its ledger impact to 0.00.
    """
    client, SessionLocal = payroll_ledger_client

    # Reverse PR-2026-10
    resp_rev = client.post(
        "/payroll/runs/PR-2026-10/reverse",
        json={
            "reversal_date": "2026-10-31",
            "reversed_by": "U-0099",
            "reason": "Correction of October bonus inputs",
        },
    )
    assert resp_rev.status_code == 200
    rev_data = resp_rev.json()
    assert rev_data["status"] == "REVERSED"
    assert rev_data["reversal_journal_entry_id"] is not None
    assert rev_data["payment_reversal_journal_entry_id"] is not None

    orig_je_id = rev_data["journal_entry_id"]
    rev_je_id = rev_data["reversal_journal_entry_id"]

    # Verify original + reversal net impact on accounts 5001..5005 is 0.00
    with SessionLocal() as db:
        net_5001_5005 = db.scalar(
            select(func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0)).where(
                JournalLine.entry_id.in_([orig_je_id, rev_je_id]),
                JournalLine.account_code.between(5001, 5005),
            )
        )
        assert round_money(net_5001_5005) == Decimal("0.00")

    # Attempting to reverse a second time is rejected with 409 RUN_ALREADY_REVERSED
    resp_rev_again = client.post(
        "/payroll/runs/PR-2026-10/reverse",
        json={"reversed_by": "U-0099"},
    )
    assert resp_rev_again.status_code == 409
    assert resp_rev_again.json()["error_code"] == "RUN_ALREADY_REVERSED"
