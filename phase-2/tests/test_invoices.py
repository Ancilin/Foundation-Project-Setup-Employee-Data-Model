"""Tests for Task 10 (LF-10): Clients, Invoices with GST, Status Lifecycle, Payments,
Draft/Cancelled non-posting guard, Sent-Cancellation reversal, and Accounts Receivable reconciliation.
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
    Client,
    Invoice,
    JournalEntry,
    JournalLine,
)

ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = ROOT / "data" / "csv"


@pytest.fixture(scope="module")
def invoice_test_client():
    """Create an isolated in-memory database seeded with chart_of_accounts, clients, invoices, and ledger entries."""
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

        # 2. Clients
        df_cl = pd.read_csv(CSV_DIR / "clients.csv")
        for _, r in df_cl.iterrows():
            session.add(
                Client(
                    client_id=str(r["client_id"]).strip(),
                    client_name=str(r["client_name"]).strip(),
                    industry=str(r["industry"]).strip(),
                    city=str(r["city"]).strip(),
                    state_or_region=str(r["state_or_region"]).strip(),
                    country=str(r["country"]).strip(),
                    client_type=str(r["client_type"]).strip(),
                    gst_registration=str(r["gst_registration"]).strip() if pd.notna(r.get("gst_registration")) else None,
                    payment_terms_days=int(r["payment_terms_days"]),
                    payment_behaviour=str(r["payment_behaviour"]).strip() if pd.notna(r.get("payment_behaviour")) else None,
                    primary_service_line=int(r["primary_service_line"]),
                    contact_email=str(r["contact_email"]).strip(),
                    onboarded_on=date.fromisoformat(str(r["onboarded_on"])[:10]),
                    is_active=str(r["is_active"]).strip(),
                )
            )

        # 3. Journal Entries & Journal Lines
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

        # 4. Official Invoices
        df_inv = pd.read_csv(CSV_DIR / "invoices.csv")
        inv_records = []
        for r in df_inv.to_dict(orient="records"):
            inv_records.append(
                {
                    "invoice_id": str(r["invoice_id"]).strip(),
                    "invoice_number": str(r["invoice_number"]).strip(),
                    "client_id": str(r["client_id"]).strip(),
                    "invoice_date": date.fromisoformat(str(r["invoice_date"])[:10]),
                    "due_date": date.fromisoformat(str(r["due_date"])[:10]),
                    "service_line_account": int(r["service_line_account"]),
                    "currency": str(r["currency"]).strip(),
                    "subtotal": Decimal(str(r["subtotal"])),
                    "gst_rate_percent": Decimal(str(r["gst_rate_percent"])),
                    "gst_amount": Decimal(str(r["gst_amount"])),
                    "total_amount": Decimal(str(r["total_amount"])),
                    "amount_paid": Decimal(str(r["amount_paid"])),
                    "balance_due": Decimal(str(r["balance_due"])),
                    "status": str(r["status"]).strip(),
                    "last_payment_date": date.fromisoformat(str(r["last_payment_date"])[:10])
                    if pd.notna(r.get("last_payment_date"))
                    else None,
                    "po_number": str(r["po_number"]).strip() if pd.notna(r.get("po_number")) else None,
                    "carried_in_from_prior_period": str(r["carried_in_from_prior_period"]).strip(),
                    "created_by": str(r["created_by"]).strip() if pd.notna(r.get("created_by")) else None,
                    "created_at": str(r["created_at"]).strip() if pd.notna(r.get("created_at")) else None,
                    "ledger_entry_id": str(r["ledger_entry_id"]).strip() if pd.notna(r.get("ledger_entry_id")) else None,
                }
            )
        session.execute(insert(Invoice), inv_records)
        session.commit()

    def _override_get_db():
        with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_receivables_list_reconciles_and_matches_three_clients(invoice_test_client: TestClient):
    """Verify Check 3 (ledger 1100 == open invoices == 139,394,278.00) and verify 3 clients' open balances."""
    resp = invoice_test_client.get("/invoices/receivables", params={"as_of_date": "2026-09-30"})
    assert resp.status_code == 200
    report = resp.json()

    assert report["is_reconciled"] is True
    assert Decimal(str(report["total_open_receivables"])) == Decimal("139394278.00")
    assert Decimal(str(report["ledger_account_1100_balance"])) == Decimal("139394278.00")
    assert Decimal(str(report["reconciled_difference"])) == Decimal("0.00")

    # Hand-check 3 clients from invoices.csv where status in (SENT, OVERDUE, PARTIALLY_PAID)
    df_inv = pd.read_csv(CSV_DIR / "invoices.csv")
    open_df = df_inv[df_inv["status"].isin(["SENT", "OVERDUE", "PARTIALLY_PAID"])]

    client_map = {c["client_id"]: c for c in report["clients"]}
    for cid in ["CL-001", "CL-004", "CL-016"]:
        expected_due = Decimal(str(open_df[open_df["client_id"] == cid]["balance_due"].sum())).quantize(Decimal("0.01"))
        expected_cnt = int((open_df["client_id"] == cid).sum())
        assert cid in client_map
        assert Decimal(str(client_map[cid]["balance_due"])) == expected_due
        assert client_map[cid]["open_invoices_count"] == expected_cnt


def test_draft_and_cancelled_invoices_never_post_to_ledger(invoice_test_client: TestClient):
    """Verify DRAFT and CANCELLED invoices never post to the ledger."""
    ar_before = Decimal(
        str(invoice_test_client.get("/ledger/accounts/1100/balance", params={"as_of_date": "2026-09-30"}).json()["balance"])
    )

    # 1. Create a DRAFT invoice
    create_resp = invoice_test_client.post(
        "/invoices",
        json={
            "invoice_id": "INV-TEST-DRAFT",
            "invoice_number": "INV/2026-27/TEST-01",
            "client_id": "CL-001",
            "invoice_date": "2026-09-15",
            "items": [
                {"description": "Custom ERP module", "quantity": "1", "unit_price": "100000.00"},
            ],
        },
    )
    assert create_resp.status_code == 201
    draft_inv = create_resp.json()
    assert draft_inv["status"] == "DRAFT"
    assert draft_inv["ledger_entry_id"] is None
    assert Decimal(str(draft_inv["subtotal"])) == Decimal("100000.00")
    assert Decimal(str(draft_inv["gst_amount"])) == Decimal("18000.00")
    assert Decimal(str(draft_inv["total_amount"])) == Decimal("118000.00")

    # 2. Attempting to post a DRAFT invoice directly is refused (422)
    post_draft = invoice_test_client.post("/invoices/INV-TEST-DRAFT/post")
    assert post_draft.status_code == 422
    assert post_draft.json()["error_code"] == "INVALID_INVOICE_STATUS_FOR_POSTING"

    # 3. Cancel the DRAFT invoice -> becomes CANCELLED, still no ledger entry
    cancel_resp = invoice_test_client.post("/invoices/INV-TEST-DRAFT/cancel")
    assert cancel_resp.status_code == 200
    cancelled_inv = cancel_resp.json()
    assert cancelled_inv["status"] == "CANCELLED"
    assert cancelled_inv["ledger_entry_id"] is None
    assert Decimal(str(cancelled_inv["balance_due"])) == Decimal("0.00")

    # 4. Attempting to post a CANCELLED invoice directly is refused (422)
    post_cancelled = invoice_test_client.post("/invoices/INV-TEST-DRAFT/post")
    assert post_cancelled.status_code == 422
    assert post_cancelled.json()["error_code"] == "INVALID_INVOICE_STATUS_FOR_POSTING"

    # 5. Ledger account 1100 is completely untouched
    ar_after = Decimal(
        str(invoice_test_client.get("/ledger/accounts/1100/balance", params={"as_of_date": "2026-09-30"}).json()["balance"])
    )
    assert ar_after == ar_before


def test_invoice_send_payment_and_sent_cancellation_lifecycle(invoice_test_client: TestClient):
    """Test full lifecycle:
    1. Create DRAFT -> Send (posts 1100 / 4001 / 2200) -> Part-Payment (reduces balance_due & credits 1100) -> Full Payment (PAID).
    2. Create another DRAFT -> Send -> Cancel (reverses ledger posting so Check 3 remains reconciled).
    """
    # Part A: Create -> Send -> Partial Payment -> Full Payment
    r_create = invoice_test_client.post(
        "/invoices",
        json={
            "invoice_id": "INV-TEST-PAY",
            "invoice_number": "INV/2026-27/TEST-02",
            "client_id": "CL-001",
            "invoice_date": "2026-09-10",
            "items": [
                {"description": "Cloud migration sprint", "quantity": "2", "unit_price": "50000.00"},
            ],
        },
    )
    assert r_create.status_code == 201

    r_send = invoice_test_client.post("/invoices/INV-TEST-PAY/send")
    assert r_send.status_code == 200
    sent_inv = r_send.json()
    assert sent_inv["status"] == "SENT"
    assert sent_inv["ledger_entry_id"] is not None
    assert Decimal(str(sent_inv["balance_due"])) == Decimal("118000.00")

    # Partial payment of 50,000.00
    r_pay1 = invoice_test_client.post(
        "/invoices/INV-TEST-PAY/payments",
        json={
            "payment_id": "PAY-TEST-01",
            "payment_date": "2026-09-18",
            "amount": "50000.00",
            "payment_mode": "NEFT",
        },
    )
    assert r_pay1.status_code == 201
    part_inv = r_pay1.json()
    assert part_inv["status"] == "PARTIALLY_PAID"
    assert Decimal(str(part_inv["amount_paid"])) == Decimal("50000.00")
    assert Decimal(str(part_inv["balance_due"])) == Decimal("68000.00")

    # Remaining payment of 68,000.00 -> PAID
    r_pay2 = invoice_test_client.post(
        "/invoices/INV-TEST-PAY/payments",
        json={
            "payment_id": "PAY-TEST-02",
            "payment_date": "2026-09-25",
            "amount": "68000.00",
            "payment_mode": "RTGS",
        },
    )
    assert r_pay2.status_code == 201
    paid_inv = r_pay2.json()
    assert paid_inv["status"] == "PAID"
    assert Decimal(str(paid_inv["amount_paid"])) == Decimal("118000.00")
    assert Decimal(str(paid_inv["balance_due"])) == Decimal("0.00")

    # Part B: Create -> Send -> Cancel (reverses ledger entry and keeps Check 3 reconciled)
    invoice_test_client.post(
        "/invoices",
        json={
            "invoice_id": "INV-TEST-CANC",
            "invoice_number": "INV/2026-27/TEST-03",
            "client_id": "CL-005",
            "invoice_date": "2026-09-20",
            "items": [
                {"description": "Advisory retainer", "quantity": "1", "unit_price": "200000.00"},
            ],
        },
    )
    invoice_test_client.post("/invoices/INV-TEST-CANC/send")
    r_cancel = invoice_test_client.post("/invoices/INV-TEST-CANC/cancel", params={"cancel_date": "2026-09-22"})
    assert r_cancel.status_code == 200
    assert r_cancel.json()["status"] == "CANCELLED"
    assert Decimal(str(r_cancel.json()["balance_due"])) == Decimal("0.00")

    # Verify Check 3 reconciliation still holds after all operations!
    rec_after = invoice_test_client.get("/invoices/receivables", params={"as_of_date": "2026-09-30"}).json()
    assert rec_after["is_reconciled"] is True
    assert Decimal(str(rec_after["reconciled_difference"])) == Decimal("0.00")
