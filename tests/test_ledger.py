"""Tests for Task 9 (LF-09): Double-entry accounting ledger, balanced entry enforcement,
read-only posted entries, reversals, account_balance(account, date), and payroll run posting.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
import pandas as pd
import pytest
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import ConflictError
from app.db.session import get_db
from app.main import app
from app.models import (
    Base,
    ChartOfAccount,
    Department,
    Employee,
    JournalEntry,
    PayrollItem,
    PayrollRun,
    Role,
)

ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = ROOT / "data" / "csv"


@pytest.fixture(scope="module")
def ledger_test_env():
    """Create an isolated in-memory database seeded with chart_of_accounts and PR-2025-04 payroll items."""
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

        # 2. Departments & Roles (needed for Employees)
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

        # 3. Employees & PR-2025-04 PayrollRun + PayrollItems
        df_emp = pd.read_csv(CSV_DIR / "employees.csv")
        emp_records = []
        for _, r in df_emp.iterrows():
            eid = str(r["employee_id"]).strip()
            emp_records.append(
                {
                    "employee_id": eid,
                    "first_name": "Emp",
                    "last_name": eid,
                    "work_email": f"{eid.lower()}@znova-demo.example",
                    "gender": str(r["gender"]).strip(),
                    "date_of_birth": date.fromisoformat(str(r["date_of_birth"])[:10]),
                    "hire_date": date.fromisoformat(str(r["hire_date"])[:10]),
                    "exit_date": date.fromisoformat(str(r["exit_date"])[:10]) if pd.notna(r.get("exit_date")) else None,
                    "employment_status": str(r["employment_status"]).strip(),
                    "employment_type": str(r["employment_type"]).strip(),
                    "department_id": str(r["department_id"]).strip(),
                    "role_id": str(r["role_id"]).strip(),
                    "manager_id": None,
                    "work_location": str(r["work_location"]).strip(),
                    "work_mode": str(r["work_mode"]).strip(),
                }
            )
        session.execute(insert(Employee), emp_records)

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
                run_by=str(pr_row["run_by"]).strip(),
            )
        )

        df_pi = pd.read_csv(CSV_DIR / "payroll_items.csv")
        df_pi = df_pi[df_pi["run_id"] == "PR-2025-04"]
        pi_records = []
        for _, r in df_pi.iterrows():
            pi_records.append(
                {
                    "payroll_item_id": str(r["payroll_item_id"]).strip(),
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
                    "variable_pay_type": str(r["variable_pay_type"]).strip() if pd.notna(r.get("variable_pay_type")) else None,
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
                    "calculation_note": str(r["calculation_note"]).strip() if pd.notna(r.get("calculation_note")) else None,
                }
            )
        session.execute(insert(PayrollItem), pi_records)
        session.commit()

    def _override_get_db():
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client, TestingSessionLocal
    app.dependency_overrides.clear()


def test_chart_of_accounts_loaded(ledger_test_env):
    """Verify all 47 accounts and 5 account types (ASSET, LIABILITY, EQUITY, INCOME, EXPENSE) are loaded."""
    client, _ = ledger_test_env
    resp = client.get("/ledger/accounts")
    assert resp.status_code == 200
    accounts = resp.json()
    assert len(accounts) == 47
    acct_types = {a["account_type"] for a in accounts}
    assert acct_types == {"ASSET", "LIABILITY", "EQUITY", "INCOME", "EXPENSE"}


def test_unbalanced_entry_is_refused_with_clear_message(ledger_test_env):
    """Refuse any journal entry where debits do not equal credits with a clear message."""
    client, _ = ledger_test_env
    unbalanced_payload = {
        "entry_date": "2025-04-15",
        "description": "Unbalanced test entry",
        "source_type": "MANUAL",
        "source_id": "MAN-UNBAL",
        "lines": [
            {"account_code": 5101, "debit": "50000.00", "credit": "0.00", "line_description": "Office rent"},
            {"account_code": 1001, "debit": "0.00", "credit": "49500.00", "line_description": "Bank payment short by 500"},
        ],
    }
    resp = client.post("/ledger/entries", json=unbalanced_payload)
    assert resp.status_code == 422
    body = resp.json()
    assert body["error_code"] == "UNBALANCED_ENTRY"
    assert "50000.00" in body["detail"]
    assert "49500.00" in body["detail"]
    assert "500.00" in body["detail"]


def test_posted_entries_are_immutable_and_reversals_work(ledger_test_env):
    """Verify posted entries cannot be edited or deleted, and corrections are made via reversing entries."""
    client, SessionLocal = ledger_test_env

    # 1. Post a valid balanced entry on 2025-04-10
    create_resp = client.post(
        "/ledger/entries",
        json={
            "entry_id": "JE-TEST-001",
            "entry_date": "2025-04-10",
            "description": "Office supplies purchase",
            "source_type": "EXPENSE",
            "source_id": "EXP-TEST-01",
            "lines": [
                {"account_code": 5112, "debit": "12500.00", "credit": "0.00", "cost_center_department_id": "D08", "line_description": "Office supplies"},
                {"account_code": 1001, "debit": "0.00", "credit": "12500.00", "line_description": "Paid from bank"},
            ],
        },
    )
    assert create_resp.status_code == 201
    entry = create_resp.json()
    assert entry["status"] == "POSTED"
    assert Decimal(str(entry["total_debit"])) == Decimal("12500.00")
    assert Decimal(str(entry["total_credit"])) == Decimal("12500.00")

    # 2. Check account_balance(5112, date): 0.00 before 2025-04-10, 12500.00 on/after 2025-04-10
    bal_before = client.get("/ledger/accounts/5112/balance", params={"as_of_date": "2025-04-09"}).json()
    assert Decimal(str(bal_before["balance"])) == Decimal("0.00")

    bal_on = client.get("/ledger/accounts/5112/balance", params={"as_of_date": "2025-04-10"}).json()
    assert Decimal(str(bal_on["balance"])) == Decimal("12500.00")

    # 3. Attempt to edit the posted entry via PATCH -> 409 Conflict (IMMUTABLE_POSTED_ENTRY)
    patch_resp = client.patch("/ledger/entries/JE-TEST-001", json={"description": "Tampered description"})
    assert patch_resp.status_code == 409
    assert patch_resp.json()["error_code"] == "IMMUTABLE_POSTED_ENTRY"

    # 4. Attempt to delete the posted entry via DELETE -> 409 Conflict (IMMUTABLE_POSTED_ENTRY)
    del_resp = client.delete("/ledger/entries/JE-TEST-001")
    assert del_resp.status_code == 409
    assert del_resp.json()["error_code"] == "IMMUTABLE_POSTED_ENTRY"

    # 5. Attempt direct SQLAlchemy ORM mutation on a POSTED entry -> raises ConflictError
    with SessionLocal() as session:
        je_obj = session.get(JournalEntry, "JE-TEST-001")
        je_obj.description = "Direct ORM edit attempt"
        with pytest.raises(ConflictError):
            session.commit()
        session.rollback()

    # 6. Post a reversing entry on 2025-04-12 -> swaps debits and credits, brings balance back to 0.00
    rev_resp = client.post(
        "/ledger/entries/JE-TEST-001/reverse",
        json={"reversal_date": "2025-04-12", "description": "Reversal of office supplies purchase"},
    )
    assert rev_resp.status_code == 201
    rev_entry = rev_resp.json()
    assert rev_entry["reversal_of_source_id"] == "EXP-TEST-01"
    assert Decimal(str(rev_entry["lines"][0]["debit"])) == Decimal("0.00")
    assert Decimal(str(rev_entry["lines"][0]["credit"])) == Decimal("12500.00")
    assert Decimal(str(rev_entry["lines"][1]["debit"])) == Decimal("12500.00")
    assert Decimal(str(rev_entry["lines"][1]["credit"])) == Decimal("0.00")

    bal_after_rev = client.get("/ledger/accounts/5112/balance", params={"as_of_date": "2025-04-12"}).json()
    assert Decimal(str(bal_after_rev["balance"])) == Decimal("0.00")


def test_post_payroll_run_matches_official_je_000105(ledger_test_env):
    """Post PR-2025-04 payroll totals to employer-cost accounts (5001..5005) and verify exact match with official JE-000105."""
    client, _ = ledger_test_env

    resp = client.post("/ledger/post-payroll/PR-2025-04")
    assert resp.status_code == 201
    je = resp.json()

    assert je["source_type"] == "PAYROLL_RUN"
    assert je["source_id"] == "PR-2025-04"
    assert Decimal(str(je["total_debit"])) == Decimal("53363392.08")
    assert Decimal(str(je["total_credit"])) == Decimal("53363392.08")
    assert len(je["lines"]) == 43

    # Compare every single line against official journal_lines.csv for JE-000105
    df_jl = pd.read_csv(CSV_DIR / "journal_lines.csv")
    off_lines = df_jl[df_jl["entry_id"] == "JE-000105"].sort_values("line_no").to_dict(orient="records")

    for gen_line, off_line in zip(je["lines"], off_lines):
        assert int(gen_line["account_code"]) == int(off_line["account_code"])
        assert Decimal(str(gen_line["debit"])) == Decimal(str(off_line["debit"])).quantize(Decimal("0.01"))
        assert Decimal(str(gen_line["credit"])) == Decimal(str(off_line["credit"])).quantize(Decimal("0.01"))
        off_dept = str(off_line["cost_center_department_id"]).strip() if pd.notna(off_line.get("cost_center_department_id")) else None
        assert gen_line["cost_center_department_id"] == off_dept
