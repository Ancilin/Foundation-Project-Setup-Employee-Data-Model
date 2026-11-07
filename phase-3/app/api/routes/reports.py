"""Financial Statements HTTP routes (Task 15 / LF-15):
- GET /reports/trial-balance
- GET /reports/profit-and-loss
- GET /reports/balance-sheet
"""

from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.report import (
    BalanceSheetReportRead,
    ProfitAndLossReportRead,
    TrialBalanceReportRead,
)
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Financial Statements (Task 15)"])


@router.get("/trial-balance", response_model=TrialBalanceReportRead)
def get_trial_balance_report(
    start_date: date | None = Query(default=None, description="Optional start date (YYYY-MM-DD)"),
    end_date: date | None = Query(default=None, description="Optional end date (YYYY-MM-DD)"),
    active_only: bool = Query(default=True, description="If True, include only leaf accounts with non-zero activity"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Build the Trial Balance for any date range. Group parent accounts are rolled up separately and never counted twice."""
    return report_service.get_trial_balance(
        session=db,
        start_date=start_date,
        end_date=end_date,
        active_only=active_only,
    )


@router.get("/profit-and-loss", response_model=ProfitAndLossReportRead)
def get_profit_and_loss_report(
    start_date: date | None = Query(default=None, description="Optional start date (YYYY-MM-DD)"),
    end_date: date | None = Query(default=None, description="Optional end date (YYYY-MM-DD)"),
    department_id: str | None = Query(default=None, description="Optional department cost-center filter (e.g. D01)"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Build the Profit & Loss statement (Revenue, Expenses, and Net Profit). Group accounts (4000, 5000) are never counted twice."""
    return report_service.get_profit_and_loss(
        session=db,
        start_date=start_date,
        end_date=end_date,
        department_id=department_id,
    )


@router.get("/balance-sheet", response_model=BalanceSheetReportRead)
def get_balance_sheet_report(
    as_of_date: date | None = Query(default=None, description="Optional cut-off date (YYYY-MM-DD)"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Build the Balance Sheet and verify Assets = Liabilities + Equity + Current Profit. Group accounts (1000, 2000, 3000) are never counted twice."""
    return report_service.get_balance_sheet(
        session=db,
        as_of_date=as_of_date,
    )
