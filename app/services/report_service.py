"""Core Financial Reports Service (Task 15 / LF-15):
- Trial Balance (for any date range, plus CSV export for verify_ledgerforge.py trial-balance)
- Profit and Loss Statement (Income & Expenses with group rollups, never double-counting group accounts)
- Balance Sheet (Assets = Liabilities + Equity + Current Profit, never double-counting group accounts)
"""

import csv
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ledger import ChartOfAccount, JournalEntry, JournalLine

TWO_PLACES = Decimal("0.01")
ROOT = Path(__file__).resolve().parent.parent
EXPORTS_DIR = ROOT / "exports"


def _to_dec(val: Decimal | int | float | str | None) -> Decimal:
    if val is None or val == "":
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def round_money(val: Decimal | int | float | str | None) -> Decimal:
    return _to_dec(val).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _aggregate_account_sums(
    session: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    department_id: str | None = None,
) -> dict[int, tuple[Decimal, Decimal]]:
    """Aggregate total debit and total credit per account_code from POSTED journal entries."""
    stmt = (
        select(
            JournalLine.account_code,
            func.coalesce(func.sum(JournalLine.debit), 0),
            func.coalesce(func.sum(JournalLine.credit), 0),
        )
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.entry_id)
        .where(JournalEntry.status == "POSTED")
    )
    if start_date is not None:
        stmt = stmt.where(JournalEntry.entry_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(JournalEntry.entry_date <= end_date)
    if department_id is not None and department_id.strip():
        stmt = stmt.where(JournalLine.cost_center_department_id == department_id.strip())

    stmt = stmt.group_by(JournalLine.account_code)
    rows = session.execute(stmt).all()
    return {
        int(acct_code): (round_money(dr), round_money(cr))
        for acct_code, dr, cr in rows
    }


def get_trial_balance(
    session: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    active_only: bool = False,
) -> dict[str, Any]:
    """Build the Trial Balance for any date range.
    Separates leaf accounts (is_group == 'N') from parent group headers (is_group == 'Y')
    so group accounts are never counted twice in total_debit or total_credit.
    """
    coa_rows = list(
        session.scalars(select(ChartOfAccount).order_by(ChartOfAccount.account_code)).all()
    )
    sums_map = _aggregate_account_sums(session, start_date=start_date, end_date=end_date)

    leaf_rows: list[dict[str, Any]] = []
    group_defs: list[ChartOfAccount] = []
    tot_debit = Decimal("0.00")
    tot_credit = Decimal("0.00")

    for acct in coa_rows:
        if acct.is_group.upper() == "Y":
            group_defs.append(acct)
            continue

        dr, cr = sums_map.get(acct.account_code, (Decimal("0.00"), Decimal("0.00")))
        if active_only and dr == Decimal("0.00") and cr == Decimal("0.00"):
            continue

        net_dr = round_money(dr - cr) if dr > cr else Decimal("0.00")
        net_cr = round_money(cr - dr) if cr > dr else Decimal("0.00")
        net_bal = (
            round_money(dr - cr)
            if acct.normal_balance.upper() == "DEBIT"
            else round_money(cr - dr)
        )

        tot_debit = round_money(tot_debit + dr)
        tot_credit = round_money(tot_credit + cr)

        leaf_rows.append(
            {
                "account_code": acct.account_code,
                "account_name": acct.account_name,
                "account_type": acct.account_type,
                "normal_balance": acct.normal_balance,
                "parent_code": acct.parent_code,
                "is_group": "N",
                "debit": dr,
                "credit": cr,
                "net_debit_balance": net_dr,
                "net_credit_balance": net_cr,
                "net_balance": net_bal,
            }
        )

    # Compute parent group rollups from leaf children only (for presentation, not added to grand totals)
    group_rollups: list[dict[str, Any]] = []
    for grp in group_defs:
        children = [r for r in leaf_rows if r["parent_code"] == grp.account_code]
        g_dr = round_money(sum((r["debit"] for r in children), Decimal("0.00")))
        g_cr = round_money(sum((r["credit"] for r in children), Decimal("0.00")))
        g_net_dr = round_money(g_dr - g_cr) if g_dr > g_cr else Decimal("0.00")
        g_net_cr = round_money(g_cr - g_dr) if g_cr > g_dr else Decimal("0.00")
        g_net_bal = (
            round_money(g_dr - g_cr)
            if grp.normal_balance.upper() == "DEBIT"
            else round_money(g_cr - g_dr)
        )
        group_rollups.append(
            {
                "account_code": grp.account_code,
                "account_name": grp.account_name,
                "account_type": grp.account_type,
                "normal_balance": grp.normal_balance,
                "parent_code": grp.parent_code,
                "is_group": "Y",
                "debit": g_dr,
                "credit": g_cr,
                "net_debit_balance": g_net_dr,
                "net_credit_balance": g_net_cr,
                "net_balance": g_net_bal,
            }
        )

    diff = round_money(tot_debit - tot_credit)
    return {
        "report_type": "TRIAL_BALANCE",
        "start_date": start_date,
        "end_date": end_date,
        "leaf_accounts_count": len(leaf_rows),
        "total_debit": tot_debit,
        "total_credit": tot_credit,
        "difference": diff,
        "is_balanced": diff == Decimal("0.00"),
        "group_rollups": group_rollups,
        "accounts": leaf_rows,
    }


def export_trial_balance_csv(
    session: Session,
    target_dir: Path | None = None,
    filename: str = "trial_balance.csv",
    start_date: date | None = None,
    end_date: date | None = None,
) -> Path:
    """Export leaf-account Trial Balance CSV compatible with `python verify_ledgerforge.py trial-balance`."""
    dst = target_dir or EXPORTS_DIR
    dst.mkdir(parents=True, exist_ok=True)
    out_path = dst / filename

    tb = get_trial_balance(session, start_date=start_date, end_date=end_date, active_only=True)
    columns = [
        "account_code",
        "account_name",
        "account_type",
        "normal_balance",
        "debit",
        "credit",
        "net_balance",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in tb["accounts"]:
            writer.writerow([str(row[col]) for col in columns])

    return out_path


def get_profit_and_loss(
    session: Session,
    start_date: date | None = None,
    end_date: date | None = None,
    department_id: str | None = None,
) -> dict[str, Any]:
    """Build the Profit & Loss statement (Income vs. Expenses) for any date range.
    Group accounts (4000 Income, 5000 Expenses) hold rolled-up totals of their leaf accounts
    and are never counted twice.
    """
    coa_rows = list(
        session.scalars(select(ChartOfAccount).order_by(ChartOfAccount.account_code)).all()
    )
    sums_map = _aggregate_account_sums(
        session,
        start_date=start_date,
        end_date=end_date,
        department_id=department_id,
    )

    income_accounts: list[dict[str, Any]] = []
    expense_accounts: list[dict[str, Any]] = []
    tot_revenue = Decimal("0.00")
    tot_expenses = Decimal("0.00")
    payroll_cost = Decimal("0.00")

    for acct in coa_rows:
        # Never count group header accounts (is_group == 'Y') in leaf rows or totals
        if acct.is_group.upper() == "Y":
            continue

        dr, cr = sums_map.get(acct.account_code, (Decimal("0.00"), Decimal("0.00")))
        if acct.account_type.upper() == "INCOME":
            amt = round_money(cr - dr)
            tot_revenue = round_money(tot_revenue + amt)
            income_accounts.append(
                {
                    "account_code": acct.account_code,
                    "account_name": acct.account_name,
                    "account_type": acct.account_type,
                    "normal_balance": acct.normal_balance,
                    "parent_code": acct.parent_code,
                    "is_group": "N",
                    "debit": dr,
                    "credit": cr,
                    "amount": amt,
                }
            )
        elif acct.account_type.upper() == "EXPENSE":
            amt = round_money(dr - cr)
            tot_expenses = round_money(tot_expenses + amt)
            if 5001 <= acct.account_code <= 5005:
                payroll_cost = round_money(payroll_cost + amt)
            expense_accounts.append(
                {
                    "account_code": acct.account_code,
                    "account_name": acct.account_name,
                    "account_type": acct.account_type,
                    "normal_balance": acct.normal_balance,
                    "parent_code": acct.parent_code,
                    "is_group": "N",
                    "debit": dr,
                    "credit": cr,
                    "amount": amt,
                }
            )

    net_profit = round_money(tot_revenue - tot_expenses)
    non_payroll_exp = round_money(tot_expenses - payroll_cost)

    return {
        "report_type": "PROFIT_AND_LOSS",
        "start_date": start_date,
        "end_date": end_date,
        "department_id": department_id,
        "income_group": {
            "group_code": 4000,
            "group_name": "Income",
            "account_type": "INCOME",
            "total_amount": tot_revenue,
            "accounts": income_accounts,
        },
        "expense_group": {
            "group_code": 5000,
            "group_name": "Expenses",
            "account_type": "EXPENSE",
            "total_amount": tot_expenses,
            "accounts": expense_accounts,
        },
        "total_revenue": tot_revenue,
        "total_expenses": tot_expenses,
        "net_profit": net_profit,
        "payroll_employer_cost_5001_5005": payroll_cost,
        "non_payroll_operating_expenses": non_payroll_exp,
        "group_accounts_excluded_from_totals": True,
    }


def get_balance_sheet(
    session: Session,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Build the Balance Sheet as of `as_of_date` (or across all posted entries if None).
    Verifies the fundamental accounting equation:
      Assets = Liabilities + Equity + Current Profit
    Never counts group accounts (1000 Assets, 2000 Liabilities, 3000 Equity) twice.
    """
    coa_rows = list(
        session.scalars(select(ChartOfAccount).order_by(ChartOfAccount.account_code)).all()
    )
    sums_map = _aggregate_account_sums(session, start_date=None, end_date=as_of_date)

    asset_accounts: list[dict[str, Any]] = []
    liability_accounts: list[dict[str, Any]] = []
    equity_accounts: list[dict[str, Any]] = []

    tot_assets = Decimal("0.00")
    tot_liabilities = Decimal("0.00")
    tot_equity = Decimal("0.00")
    tot_income = Decimal("0.00")
    tot_expense = Decimal("0.00")

    for acct in coa_rows:
        # Exclude group parent accounts (1000, 2000, 3000, 4000, 5000) from leaf calculations
        if acct.is_group.upper() == "Y":
            continue

        dr, cr = sums_map.get(acct.account_code, (Decimal("0.00"), Decimal("0.00")))
        atype = acct.account_type.upper()

        if atype == "ASSET":
            # Net carrying value of asset is debit - credit (so contra-asset 1590 Accumulated Depreciation reduces Assets)
            amt = round_money(dr - cr)
            tot_assets = round_money(tot_assets + amt)
            asset_accounts.append(
                {
                    "account_code": acct.account_code,
                    "account_name": acct.account_name,
                    "account_type": acct.account_type,
                    "normal_balance": acct.normal_balance,
                    "parent_code": acct.parent_code,
                    "is_group": "N",
                    "debit": dr,
                    "credit": cr,
                    "amount": amt,
                }
            )
        elif atype == "LIABILITY":
            amt = round_money(cr - dr)
            tot_liabilities = round_money(tot_liabilities + amt)
            liability_accounts.append(
                {
                    "account_code": acct.account_code,
                    "account_name": acct.account_name,
                    "account_type": acct.account_type,
                    "normal_balance": acct.normal_balance,
                    "parent_code": acct.parent_code,
                    "is_group": "N",
                    "debit": dr,
                    "credit": cr,
                    "amount": amt,
                }
            )
        elif atype == "EQUITY":
            amt = round_money(cr - dr)
            tot_equity = round_money(tot_equity + amt)
            equity_accounts.append(
                {
                    "account_code": acct.account_code,
                    "account_name": acct.account_name,
                    "account_type": acct.account_type,
                    "normal_balance": acct.normal_balance,
                    "parent_code": acct.parent_code,
                    "is_group": "N",
                    "debit": dr,
                    "credit": cr,
                    "amount": amt,
                }
            )
        elif atype == "INCOME":
            tot_income = round_money(tot_income + (cr - dr))
        elif atype == "EXPENSE":
            tot_expense = round_money(tot_expense + (dr - cr))

    current_profit = round_money(tot_income - tot_expense)
    tot_equity_and_profit = round_money(tot_equity + current_profit)
    tot_liab_and_eq = round_money(tot_liabilities + tot_equity_and_profit)
    eq_diff = round_money(tot_assets - tot_liab_and_eq)

    return {
        "report_type": "BALANCE_SHEET",
        "as_of_date": as_of_date,
        "assets_group": {
            "group_code": 1000,
            "group_name": "Assets",
            "account_type": "ASSET",
            "total_amount": tot_assets,
            "accounts": asset_accounts,
        },
        "liabilities_group": {
            "group_code": 2000,
            "group_name": "Liabilities",
            "account_type": "LIABILITY",
            "total_amount": tot_liabilities,
            "accounts": liability_accounts,
        },
        "equity_group": {
            "group_code": 3000,
            "group_name": "Equity",
            "account_type": "EQUITY",
            "total_amount": tot_equity,
            "accounts": equity_accounts,
        },
        "total_assets": tot_assets,
        "total_liabilities": tot_liabilities,
        "total_equity_before_current_profit": tot_equity,
        "current_period_profit": current_profit,
        "total_equity_and_profit": tot_equity_and_profit,
        "total_liabilities_and_equity": tot_liab_and_eq,
        "accounting_equation_difference": eq_diff,
        "is_balanced": eq_diff == Decimal("0.00"),
        "group_accounts_excluded_from_totals": True,
    }
