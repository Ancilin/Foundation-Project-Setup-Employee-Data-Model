"""Tests for Core Financial Statements (Task 15 / LF-15):
1. Trial Balance (for full period and custom date ranges, verifying debits == credits and group rollups are not double-counted).
2. Profit & Loss Statement (verifying revenue, expenses, net profit, and group exclusion).
3. Balance Sheet (verifying Assets = Liabilities + Equity + Current Profit and contra-asset handling).
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
    ChartOfAccount,
    Department,
    Employee,
    Role,
    User,
)
from app.services.ledger_service import create_journal_entry
from app.services.report_service import export_trial_balance_csv


@pytest.fixture()
def financial_reports_client():
    """Create an isolated in-memory database with Chart of Accounts (including parent group accounts 1000..5000
    and contra-asset 1590 Accumulated Depreciation) and balanced journal entries across two months.
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
                role_title="Finance Lead",
                level=3,
                grade="G3",
                band_min_annual=800000,
                band_mid_annual=1200000,
                band_max_annual=1600000,
                overtime_eligible=False,
            )
        )
        session.add(
            Employee(
                employee_id="EMP-0099",
                first_name="Sanjay",
                last_name="Kumar",
                work_email="sanjay.kumar@znova-demo.example",
                gender="Male",
                date_of_birth=date(1988, 3, 15),
                hire_date=date(2022, 4, 1),
                employment_status="Active",
                employment_type="Permanent",
                department_id="D01",
                role_id="R01",
                work_location="Bengaluru",
                work_mode="Hybrid",
            )
        )
        session.add(
            User(
                user_id="U-0099",
                employee_id="EMP-0099",
                username="sanjay.kumar@znova-demo.example",
                role="ADMIN",
                password_hash=hash_password(DEFAULT_DEMO_PASSWORD, rounds=4),
                is_active="Y",
                mfa_enabled="Y",
            )
        )

        # Seed group accounts (1000..5000) and leaf accounts
        coa_seed = [
            (1000, "Assets", "ASSET", "DEBIT", None, "Y", "Balance Sheet"),
            (1001, "Bank - Operating Account", "ASSET", "DEBIT", 1000, "N", "Balance Sheet"),
            (1100, "Accounts Receivable", "ASSET", "DEBIT", 1000, "N", "Balance Sheet"),
            (1500, "Fixed Assets - Gross Block", "ASSET", "DEBIT", 1000, "N", "Balance Sheet"),
            (1590, "Accumulated Depreciation", "ASSET", "CREDIT", 1000, "N", "Balance Sheet"),
            (2000, "Liabilities", "LIABILITY", "CREDIT", None, "Y", "Balance Sheet"),
            (2001, "Accounts Payable", "LIABILITY", "CREDIT", 2000, "N", "Balance Sheet"),
            (2100, "Salaries Payable", "LIABILITY", "CREDIT", 2000, "N", "Balance Sheet"),
            (3000, "Equity", "EQUITY", "CREDIT", None, "Y", "Balance Sheet"),
            (3001, "Share Capital", "EQUITY", "CREDIT", 3000, "N", "Balance Sheet"),
            (3100, "Retained Earnings", "EQUITY", "CREDIT", 3000, "N", "Balance Sheet"),
            (4000, "Income", "INCOME", "CREDIT", None, "Y", "Profit & Loss"),
            (4001, "Software Services Revenue", "INCOME", "CREDIT", 4000, "N", "Profit & Loss"),
            (5000, "Expenses", "EXPENSE", "DEBIT", None, "Y", "Profit & Loss"),
            (5001, "Salaries & Wages", "EXPENSE", "DEBIT", 5000, "N", "Profit & Loss"),
            (5101, "Office Rent", "EXPENSE", "DEBIT", 5000, "N", "Profit & Loss"),
            (5201, "Depreciation", "EXPENSE", "DEBIT", 5000, "N", "Profit & Loss"),
        ]
        for code, name, atype, nbal, pcode, grp, stmt_type in coa_seed:
            session.add(
                ChartOfAccount(
                    account_code=code,
                    account_name=name,
                    account_type=atype,
                    normal_balance=nbal,
                    parent_code=pcode,
                    is_group=grp,
                    statement=stmt_type,
                    is_active="Y",
                )
            )
        session.commit()

        # Entry 1 (2025-04-01): Initial capital & equipment
        create_journal_entry(
            session=session,
            entry_id="JE-REP-0001",
            entry_date=date(2025, 4, 1),
            description="Opening capital and fixed assets",
            source_type="OPENING",
            source_id="OPEN-001",
            lines=[
                {"account_code": 1001, "debit": "500000.00", "credit": "0.00"},
                {"account_code": 1500, "debit": "200000.00", "credit": "0.00"},
                {"account_code": 3001, "debit": "0.00", "credit": "600000.00"},
                {"account_code": 3100, "debit": "0.00", "credit": "100000.00"},
            ],
        )

        # Entry 2 (2025-04-15): Client invoice revenue
        create_journal_entry(
            session=session,
            entry_id="JE-REP-0002",
            entry_date=date(2025, 4, 15),
            description="Software services invoice",
            source_type="INVOICE",
            source_id="INV-001",
            lines=[
                {"account_code": 1100, "debit": "300000.00", "credit": "0.00"},
                {"account_code": 4001, "debit": "0.00", "credit": "300000.00"},
            ],
        )

        # Entry 3 (2025-05-10): Salaries, Office Rent, and Depreciation
        create_journal_entry(
            session=session,
            entry_id="JE-REP-0003",
            entry_date=date(2025, 5, 10),
            description="May salaries, rent, and depreciation",
            source_type="ADJUSTMENT",
            source_id="ADJ-001",
            lines=[
                {"account_code": 5001, "debit": "120000.00", "credit": "0.00", "cost_center_department_id": "D01"},
                {"account_code": 5101, "debit": "40000.00", "credit": "0.00", "cost_center_department_id": "D01"},
                {"account_code": 5201, "debit": "10000.00", "credit": "0.00"},
                {"account_code": 2100, "debit": "0.00", "credit": "120000.00"},
                {"account_code": 2001, "debit": "0.00", "credit": "40000.00"},
                {"account_code": 1590, "debit": "0.00", "credit": "10000.00"},
            ],
        )

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
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"username": "U-0099", "password": DEFAULT_DEMO_PASSWORD},
        )
        headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
        yield client, headers, TestingSessionLocal


def test_trial_balance_report_and_date_range(financial_reports_client, tmp_path):
    """Test GET /api/v1/reports/trial-balance for full period and custom date range,
    verifying total_debit == total_credit, 0 difference, and no group double-counting.
    """
    client, headers, SessionLocal = financial_reports_client

    # Full period Trial Balance: 700,000 + 300,000 + 170,000 = 1,170,000
    resp = client.get("/api/v1/reports/trial-balance", headers=headers)
    assert resp.status_code == 200
    tb = resp.json()
    assert tb["is_balanced"] is True
    assert Decimal(str(tb["difference"])) == Decimal("0.00")
    assert Decimal(str(tb["total_debit"])) == Decimal("1170000.00")
    assert Decimal(str(tb["total_credit"])) == Decimal("1170000.00")

    # Verify group accounts (1000..5000) are in group_rollups and NOT in leaf accounts
    leaf_codes = {r["account_code"] for r in tb["accounts"]}
    assert {1000, 2000, 3000, 4000, 5000}.isdisjoint(leaf_codes)
    assert {r["account_code"] for r in tb["group_rollups"]} == {1000, 2000, 3000, 4000, 5000}

    # Date range filter (April 2025 only: 700,000 + 300,000 = 1,000,000)
    resp_apr = client.get(
        "/api/v1/reports/trial-balance?start_date=2025-04-01&end_date=2025-04-30",
        headers=headers,
    )
    assert resp_apr.status_code == 200
    tb_apr = resp_apr.json()
    assert tb_apr["is_balanced"] is True
    assert Decimal(str(tb_apr["total_debit"])) == Decimal("1000000.00")
    assert Decimal(str(tb_apr["total_credit"])) == Decimal("1000000.00")

    # Verify CSV export
    with SessionLocal() as session:
        csv_file = export_trial_balance_csv(session, target_dir=tmp_path)
        assert csv_file.exists()


def test_profit_and_loss_report_no_group_double_counting(financial_reports_client):
    """Test GET /api/v1/reports/profit-and-loss verifies Revenue, Expenses, and Net Profit
    without counting group accounts 4000 or 5000 twice.
    """
    client, headers, _ = financial_reports_client
    resp = client.get("/api/v1/reports/profit-and-loss", headers=headers)
    assert resp.status_code == 200
    pnl = resp.json()

    # Revenue = 300,000.00; Expenses = 120,000 + 40,000 + 10,000 = 170,000.00; Net Profit = 130,000.00
    assert pnl["group_accounts_excluded_from_totals"] is True
    assert Decimal(str(pnl["total_revenue"])) == Decimal("300000.00")
    assert Decimal(str(pnl["total_expenses"])) == Decimal("170000.00")
    assert Decimal(str(pnl["net_profit"])) == Decimal("130000.00")
    assert Decimal(str(pnl["income_group"]["total_amount"])) == Decimal("300000.00")
    assert Decimal(str(pnl["expense_group"]["total_amount"])) == Decimal("170000.00")


def test_balance_sheet_report_accounting_equation(financial_reports_client):
    """Test GET /api/v1/reports/balance-sheet verifies:
    Assets = Liabilities + Equity + Current Profit (with contra-asset 1590 reducing Assets).
    """
    client, headers, _ = financial_reports_client
    resp = client.get("/api/v1/reports/balance-sheet", headers=headers)
    assert resp.status_code == 200
    bs = resp.json()

    # Assets = Bank (500k) + AR (300k) + Fixed Assets (200k) - Accum Depr (10k) = 990,000.00
    # Liabilities = AP (40k) + Salaries Payable (120k) = 160,000.00
    # Equity = Share Capital (600k) + Retained Earnings (100k) = 700,000.00
    # Current Profit = 130,000.00
    # Liabilities + Equity + Current Profit = 160,000 + 700,000 + 130,000 = 990,000.00
    assert bs["is_balanced"] is True
    assert Decimal(str(bs["accounting_equation_difference"])) == Decimal("0.00")
    assert Decimal(str(bs["total_assets"])) == Decimal("990000.00")
    assert Decimal(str(bs["total_liabilities"])) == Decimal("160000.00")
    assert Decimal(str(bs["total_equity_before_current_profit"])) == Decimal("700000.00")
    assert Decimal(str(bs["current_period_profit"])) == Decimal("130000.00")
    assert Decimal(str(bs["total_liabilities_and_equity"])) == Decimal("990000.00")
