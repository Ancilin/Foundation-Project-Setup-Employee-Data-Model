"""Tests for Task 11 (LF-11): Vendors, Expense Bills, Approval & Separation of Duties,
Ledger Posting on Approval & Payment, Spend Report, Monthly Reconciliation with CSV, and Duplicate Detection.
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

from app.db.session import get_db
from app.main import app
from app.models import (
    Base,
    ChartOfAccount,
    Department,
    Expense,
    JournalEntry,
    JournalLine,
    Vendor,
)
from app.services.ledger_service import account_balance

ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = ROOT / "data" / "csv"


@pytest.fixture(scope="module")
def expense_test_client():
    """Create an isolated in-memory database seeded with chart_of_accounts, departments,
    vendors, expenses, and ledger entries/lines from CSV.
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

        # 2. Departments
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

        # 3. Vendors
        df_v = pd.read_csv(CSV_DIR / "vendors.csv")
        for _, r in df_v.iterrows():
            session.add(
                Vendor(
                    vendor_id=str(r["vendor_id"]).strip(),
                    vendor_name=str(r["vendor_name"]).strip(),
                    primary_expense_account=int(r["primary_expense_account"]),
                    payment_terms_days=int(r["payment_terms_days"]),
                    city=str(r["city"]).strip(),
                    gst_registration=str(r["gst_registration"]).strip()
                    if pd.notna(r.get("gst_registration"))
                    else None,
                    is_active=str(r["is_active"]).strip(),
                )
            )

        # 4. Journal Entries & Journal Lines
        df_je = pd.read_csv(CSV_DIR / "journal_entries.csv")
        je_records = []
        for r in df_je.to_dict(orient="records"):
            je_records.append(
                {
                    "entry_id": str(r["entry_id"]).strip(),
                    "entry_date": date.fromisoformat(str(r["entry_date"])[:10]),
                    "posting_period": str(r["posting_period"]).strip(),
                    "financial_year": str(r["financial_year"]).strip(),
                    "description": str(r["description"]).strip(),
                    "source_type": str(r["source_type"]).strip(),
                    "source_id": str(r["source_id"]).strip(),
                    "status": str(r["status"]).strip(),
                    "total_debit": Decimal(str(r["total_debit"])),
                    "total_credit": Decimal(str(r["total_credit"])),
                    "reversal_of_source_id": str(r["reversal_of_source_id"]).strip()
                    if pd.notna(r.get("reversal_of_source_id"))
                    else None,
                    "created_by": str(r["created_by"]).strip() if pd.notna(r.get("created_by")) else None,
                    "created_at": str(r["created_at"]).strip() if pd.notna(r.get("created_at")) else None,
                }
            )
        session.execute(insert(JournalEntry), je_records)

        df_jl = pd.read_csv(CSV_DIR / "journal_lines.csv")
        jl_records = []
        for r in df_jl.to_dict(orient="records"):
            jl_records.append(
                {
                    "line_id": str(r["line_id"]).strip(),
                    "entry_id": str(r["entry_id"]).strip(),
                    "line_no": int(r["line_no"]),
                    "account_code": int(r["account_code"]),
                    "debit": Decimal(str(r["debit"])),
                    "credit": Decimal(str(r["credit"])),
                    "cost_center_department_id": str(r["cost_center_department_id"]).strip()
                    if pd.notna(r.get("cost_center_department_id"))
                    else None,
                    "line_description": str(r["line_description"]).strip()
                    if pd.notna(r.get("line_description"))
                    else None,
                }
            )
        session.execute(insert(JournalLine), jl_records)

        # 5. Expenses
        df_exp = pd.read_csv(CSV_DIR / "expenses.csv")
        exp_records = []
        for r in df_exp.to_dict(orient="records"):
            exp_records.append(
                {
                    "expense_id": str(r["expense_id"]).strip(),
                    "expense_date": date.fromisoformat(str(r["expense_date"])[:10]),
                    "category_account": int(r["category_account"]),
                    "vendor_id": str(r["vendor_id"]).strip(),
                    "bill_reference": str(r["bill_reference"]).strip(),
                    "description": str(r["description"]).strip(),
                    "department_id": str(r["department_id"]).strip(),
                    "amount_excl_gst": Decimal(str(r["amount_excl_gst"])),
                    "gst_rate_percent": Decimal(str(r["gst_rate_percent"])),
                    "gst_amount": Decimal(str(r["gst_amount"])),
                    "total_amount": Decimal(str(r["total_amount"])),
                    "due_date": date.fromisoformat(str(r["due_date"])[:10]),
                    "paid_date": date.fromisoformat(str(r["paid_date"])[:10])
                    if pd.notna(r.get("paid_date")) and str(r.get("paid_date")).strip() != ""
                    else None,
                    "status": str(r["status"]).strip(),
                    "payment_mode": str(r["payment_mode"]).strip()
                    if pd.notna(r.get("payment_mode")) and str(r.get("payment_mode")).strip() != ""
                    else None,
                    "submitted_by": str(r["submitted_by"]).strip(),
                    "approved_by": str(r["approved_by"]).strip()
                    if pd.notna(r.get("approved_by")) and str(r.get("approved_by")).strip() != ""
                    else None,
                    "ledger_entry_id": str(r["ledger_entry_id"]).strip()
                    if pd.notna(r.get("ledger_entry_id")) and str(r.get("ledger_entry_id")).strip() != ""
                    else None,
                    "payment_ledger_entry_id": str(r["payment_ledger_entry_id"]).strip()
                    if pd.notna(r.get("payment_ledger_entry_id"))
                    and str(r.get("payment_ledger_entry_id")).strip() != ""
                    else None,
                }
            )
        session.execute(insert(Expense), exp_records)
        session.commit()

    def override_get_db():
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c, TestingSessionLocal
    app.dependency_overrides.clear()
    engine.dispose()


def test_vendors_and_monthly_reconciliation_matches_csv(expense_test_client):
    """Verify vendors load properly and all 18 monthly totals match expenses.csv and ledger 5101..5112."""
    client, _ = expense_test_client

    # 1. Vendors list
    resp_v = client.get("/expenses/vendors")
    assert resp_v.status_code == 200
    vendors = resp_v.json()
    assert len(vendors) == 30
    assert vendors[0]["vendor_id"] == "V-001"
    assert vendors[0]["primary_expense_account"] == 5101

    # 2. Monthly reconciliation against expenses.csv
    resp_rec = client.get("/expenses/reconciliation/monthly")
    assert resp_rec.status_code == 200
    rec = resp_rec.json()
    assert rec["total_months"] == 18
    assert rec["all_months_match"] is True
    assert Decimal(rec["max_monthly_difference"]) == Decimal("0.00")
    assert Decimal(rec["total_db_amount_excl_gst"]) == Decimal("168245930.00")
    assert Decimal(rec["total_csv_amount_excl_gst"]) == Decimal("168245930.00")
    assert Decimal(rec["total_ledger_expense_debit"]) == Decimal("168245930.00")
    assert Decimal(rec["total_db_total_amount"]) == Decimal("197476837.90")
    assert Decimal(rec["total_csv_total_amount"]) == Decimal("197476837.90")

    for m in rec["months"]:
        assert m["matches"] is True
        assert Decimal(m["difference_excl_gst"]) == Decimal("0.00")
        assert Decimal(m["difference_total"]) == Decimal("0.00")

    # 3. Spend report by vendor and month & AP 2001 reconciliation
    resp_rep = client.get("/expenses/report")
    assert resp_rep.status_code == 200
    rep = resp_rep.json()
    assert rep["total_bills"] == 501
    assert rep["is_payable_reconciled"] is True
    assert Decimal(rep["payable_reconciled_difference"]) == Decimal("0.00")
    assert Decimal(rep["ledger_account_2001_balance"]) == Decimal("11646021.20")
    assert Decimal(rep["total_unpaid_payable"]) == Decimal("11646021.20")
    assert len(rep["by_vendor"]) == 30
    assert len(rep["by_month"]) == 18


def test_bill_cannot_be_paid_before_approval_and_separation_of_duties(expense_test_client):
    """Verify:
    1) A submitted bill does NOT post to the ledger until approved.
    2) A bill CANNOT be paid before approval.
    3) Separation of duties stops the submitter from approving their own bill.
    4) Approving by a different person posts Expense (5105) & GST Input (1200) and Payable (2001).
    5) Paying the approved bill clears Payable (2001) and credits Bank (1001) without counting expense twice.
    """
    client, SessionLocal = expense_test_client

    with SessionLocal() as db:
        before_5105 = account_balance(db, 5105)["balance"]
        before_1200 = account_balance(db, 1200)["balance"]
        before_2001 = account_balance(db, 2001)["balance"]
        before_1001 = account_balance(db, 1001)["balance"]

    # 1. Submit a new bill (status = SUBMITTED)
    submit_payload = {
        "expense_id": "EXP-09001",
        "expense_date": "2026-10-05",
        "vendor_id": "V-010",  # CodeCraft Tools, primary_expense_account = 5105
        "bill_reference": "BILL-2610-9001",
        "description": "DevSecOps Licence Renewal - Oct 2026",
        "department_id": "D02",
        "amount_excl_gst": "100000.00",
        "gst_rate_percent": "18.00",
        "submitted_by": "EMP-0279",
    }
    resp_sub = client.post("/expenses", json=submit_payload)
    assert resp_sub.status_code == 201
    bill = resp_sub.json()
    assert bill["expense_id"] == "EXP-09001"
    assert bill["status"] == "SUBMITTED"
    assert bill["approved_by"] is None
    assert bill["ledger_entry_id"] is None
    assert Decimal(bill["gst_amount"]) == Decimal("18000.00")
    assert Decimal(bill["total_amount"]) == Decimal("118000.00")

    # Verify SUBMITTED bill did NOT touch the ledger
    with SessionLocal() as db:
        assert account_balance(db, 5105)["balance"] == before_5105
        assert account_balance(db, 2001)["balance"] == before_2001

    # 2. Attempt to pay BEFORE approval -> must fail with 422 BILL_NOT_APPROVED
    resp_pay_early = client.post(
        "/expenses/EXP-09001/pay",
        json={"paid_date": "2026-10-10", "payment_mode": "NEFT"},
    )
    assert resp_pay_early.status_code == 422
    assert resp_pay_early.json()["error_code"] == "BILL_NOT_APPROVED"

    # 3. Attempt self-approval (submitted_by == approved_by) -> must fail with 422 SEPARATION_OF_DUTIES_VIOLATION
    resp_self_approve = client.post(
        "/expenses/EXP-09001/approve",
        json={"approved_by": "EMP-0279"},
    )
    assert resp_self_approve.status_code == 422
    assert resp_self_approve.json()["error_code"] == "SEPARATION_OF_DUTIES_VIOLATION"

    # 4. Approve by a different manager (EMP-0065) -> transitions to APPROVED and posts to ledger
    resp_approve = client.post(
        "/expenses/EXP-09001/approve",
        json={"approved_by": "EMP-0065"},
    )
    assert resp_approve.status_code == 200
    approved_bill = resp_approve.json()
    assert approved_bill["status"] == "APPROVED"
    assert approved_bill["approved_by"] == "EMP-0065"
    assert approved_bill["ledger_entry_id"] is not None

    with SessionLocal() as db:
        after_approve_5105 = account_balance(db, 5105)["balance"]
        after_approve_1200 = account_balance(db, 1200)["balance"]
        after_approve_2001 = account_balance(db, 2001)["balance"]
        assert after_approve_5105 - before_5105 == Decimal("100000.00")
        assert after_approve_1200 - before_1200 == Decimal("18000.00")
        assert after_approve_2001 - before_2001 == Decimal("118000.00")

    # 5. Pay the approved bill -> transitions to PAID, clears Payable (2001), credits Bank (1001),
    #    and does NOT hit Expense (5105) a second time!
    resp_pay = client.post(
        "/expenses/EXP-09001/pay",
        json={"paid_date": "2026-10-12", "payment_mode": "NEFT"},
    )
    assert resp_pay.status_code == 200
    paid_bill = resp_pay.json()
    assert paid_bill["status"] == "PAID"
    assert paid_bill["paid_date"] == "2026-10-12"
    assert paid_bill["payment_mode"] == "NEFT"
    assert paid_bill["payment_ledger_entry_id"] is not None

    with SessionLocal() as db:
        after_pay_5105 = account_balance(db, 5105)["balance"]
        after_pay_2001 = account_balance(db, 2001)["balance"]
        after_pay_1001 = account_balance(db, 1001)["balance"]

        # Expense account 5105 was NOT counted twice
        assert after_pay_5105 == after_approve_5105
        assert after_pay_5105 - before_5105 == Decimal("100000.00")

        # Accounts Payable 2001 was cleared back to its pre-bill balance
        assert after_pay_2001 == before_2001

        # Bank 1001 decreased by total_amount (118,000.00)
        assert before_1001 - after_pay_1001 == Decimal("118000.00")

    # 6. Paying a second time must be rejected with 409 Conflict
    resp_pay_twice = client.post(
        "/expenses/EXP-09001/pay",
        json={"paid_date": "2026-10-15", "payment_mode": "NEFT"},
    )
    assert resp_pay_twice.status_code == 409
    assert resp_pay_twice.json()["error_code"] == "BILL_ALREADY_PAID"


def test_duplicate_bill_detector(expense_test_client):
    """Test duplicate detection:
    1) Pre-submission duplicate check endpoint flags same (vendor, amount, date) and same (vendor, bill_reference).
    2) Submitting a duplicate bill without allow_duplicate=True raises 409 DUPLICATE_EXPENSE_BILL.
    3) When a duplicate is forced in (allow_duplicate=True), GET /expenses/duplicates detects and reports the pair.
    """
    client, _ = expense_test_client

    # 1. Check candidate that duplicates EXP-00001 (V-002, 2025-04-01, excl=70650, total=83367, BILL-2504-9791)
    resp_chk = client.post(
        "/expenses/duplicates/check",
        json={
            "vendor_id": "V-002",
            "expense_date": "2025-04-01",
            "amount_excl_gst": "70650.00",
            "bill_reference": "BILL-2504-9999",
            "window_days": 0,
        },
    )
    assert resp_chk.status_code == 200
    candidates = resp_chk.json()
    assert len(candidates) >= 1
    assert candidates[0]["expense_id"] == "EXP-00001"
    assert "Same vendor, amount, and expense_date" in candidates[0]["reason"]

    # 2. Attempting to submit a duplicate of EXP-09001 (V-010, 2026-10-05, 100000.00) -> 409 Conflict
    dup_payload = {
        "expense_id": "EXP-09002",
        "expense_date": "2026-10-05",
        "vendor_id": "V-010",
        "bill_reference": "BILL-2610-9002",
        "description": "Duplicate DevSecOps Licence Renewal",
        "department_id": "D02",
        "amount_excl_gst": "100000.00",
        "gst_rate_percent": "18.00",
        "submitted_by": "EMP-0279",
    }
    resp_dup_blocked = client.post("/expenses", json=dup_payload)
    assert resp_dup_blocked.status_code == 409
    assert resp_dup_blocked.json()["error_code"] == "DUPLICATE_EXPENSE_BILL"

    # 3. Also test duplicate bill_reference on a different date -> 409 Conflict
    dup_ref_payload = {
        "expense_id": "EXP-09003",
        "expense_date": "2026-10-19",
        "vendor_id": "V-010",
        "bill_reference": "BILL-2610-9001",  # already used by EXP-09001
        "description": "Different date but identical vendor bill_reference",
        "department_id": "D02",
        "amount_excl_gst": "45000.00",
        "gst_rate_percent": "18.00",
        "submitted_by": "EMP-0279",
    }
    resp_ref_blocked = client.post("/expenses", json=dup_ref_payload)
    assert resp_ref_blocked.status_code == 409
    assert resp_ref_blocked.json()["error_code"] == "DUPLICATE_EXPENSE_BILL"

    # 4. Force insert with allow_duplicate=True so we can verify the database-wide duplicate scanner
    dup_payload["allow_duplicate"] = True
    resp_forced = client.post("/expenses", json=dup_payload)
    assert resp_forced.status_code == 201

    resp_scan = client.get("/expenses/duplicates")
    assert resp_scan.status_code == 200
    scan_report = resp_scan.json()
    assert scan_report["duplicate_groups_count"] >= 1
    pair_ids = {(p["first_expense_id"], p["second_expense_id"]) for p in scan_report["duplicates"]}
    assert ("EXP-09001", "EXP-09002") in pair_ids
