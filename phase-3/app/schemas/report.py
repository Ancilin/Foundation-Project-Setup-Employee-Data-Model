"""Pydantic schemas for Core Financial Statements (Task 15 / LF-15):
- Trial Balance (for any date range)
- Profit & Loss (Income Statement, with group rollups and no double-counting)
- Balance Sheet (Assets = Liabilities + Equity + Current Profit)
"""

from datetime import date
from decimal import Decimal
from pydantic import BaseModel


class TrialBalanceRowRead(BaseModel):
    account_code: int
    account_name: str
    account_type: str
    normal_balance: str
    parent_code: int | None = None
    is_group: str = "N"
    debit: Decimal
    credit: Decimal
    net_debit_balance: Decimal
    net_credit_balance: Decimal
    net_balance: Decimal


class TrialBalanceReportRead(BaseModel):
    report_type: str = "TRIAL_BALANCE"
    start_date: date | None = None
    end_date: date | None = None
    leaf_accounts_count: int
    total_debit: Decimal
    total_credit: Decimal
    difference: Decimal
    is_balanced: bool
    group_rollups: list[TrialBalanceRowRead]
    accounts: list[TrialBalanceRowRead]


class StatementAccountLineRead(BaseModel):
    account_code: int
    account_name: str
    account_type: str
    normal_balance: str
    parent_code: int | None = None
    is_group: str = "N"
    debit: Decimal
    credit: Decimal
    amount: Decimal


class StatementGroupSectionRead(BaseModel):
    group_code: int
    group_name: str
    account_type: str
    total_amount: Decimal
    accounts: list[StatementAccountLineRead]


class ProfitAndLossReportRead(BaseModel):
    report_type: str = "PROFIT_AND_LOSS"
    start_date: date | None = None
    end_date: date | None = None
    department_id: str | None = None
    income_group: StatementGroupSectionRead
    expense_group: StatementGroupSectionRead
    total_revenue: Decimal
    total_expenses: Decimal
    net_profit: Decimal
    payroll_employer_cost_5001_5005: Decimal
    non_payroll_operating_expenses: Decimal
    group_accounts_excluded_from_totals: bool = True


class BalanceSheetReportRead(BaseModel):
    report_type: str = "BALANCE_SHEET"
    as_of_date: date | None = None
    assets_group: StatementGroupSectionRead
    liabilities_group: StatementGroupSectionRead
    equity_group: StatementGroupSectionRead
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity_before_current_profit: Decimal
    current_period_profit: Decimal
    total_equity_and_profit: Decimal
    total_liabilities_and_equity: Decimal
    accounting_equation_difference: Decimal
    is_balanced: bool
    group_accounts_excluded_from_totals: bool = True
