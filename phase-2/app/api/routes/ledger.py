"""Double-Entry Accounting Ledger HTTP routes (LF-09):
Chart of accounts, balanced journal entries, read-only posted entries, reversals, account balances, and payroll posting.
"""

from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ledger import (
    AccountBalanceRead,
    ChartOfAccountRead,
    JournalEntryCreateRequest,
    JournalEntryRead,
    JournalEntryReverseRequest,
    JournalEntryUpdateRequest,
)
from app.services import ledger_service

router = APIRouter(prefix="/ledger", tags=["Ledger"])


@router.get("/accounts", response_model=list[ChartOfAccountRead])
def get_chart_of_accounts(db: Session = Depends(get_db)):
    """List the full Chart of Accounts (Assets, Liabilities, Equity, Income, Expenses)."""
    return ledger_service.list_chart_of_accounts(db)


@router.get("/accounts/{account_code}/balance", response_model=AccountBalanceRead)
def get_account_balance(
    account_code: int,
    as_of_date: date | None = Query(default=None, description="Balance as of date (YYYY-MM-DD), defaults to today"),
    db: Session = Depends(get_db),
):
    """Calculate the balance of an account on or before a given date."""
    return ledger_service.account_balance(db, account_code=account_code, as_of_date=as_of_date)


@router.post("/entries", response_model=JournalEntryRead, status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: JournalEntryCreateRequest,
    db: Session = Depends(get_db),
):
    """Create and post a double-entry journal entry. Refuses any entry where debits != credits."""
    return ledger_service.create_journal_entry(
        session=db,
        lines=payload.lines,
        entry_date=payload.entry_date,
        description=payload.description,
        source_type=payload.source_type,
        source_id=payload.source_id,
        entry_id=payload.entry_id,
        created_by=payload.created_by,
        reversal_of_source_id=payload.reversal_of_source_id,
    )


@router.get("/entries/{entry_id}", response_model=JournalEntryRead)
def get_entry(
    entry_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve a journal entry and all its lines by entry_id."""
    return ledger_service.get_journal_entry_with_lines(db, entry_id=entry_id)


@router.patch("/entries/{entry_id}", response_model=JournalEntryRead)
def update_entry(
    entry_id: str,
    payload: JournalEntryUpdateRequest,
    db: Session = Depends(get_db),
):
    """Attempt to update a journal entry. Posted entries are read-only and refuse edits (409 Conflict)."""
    return ledger_service.update_journal_entry(
        session=db,
        entry_id=entry_id,
        description=payload.description,
        entry_date=payload.entry_date,
    )


@router.delete("/entries/{entry_id}")
def delete_entry(
    entry_id: str,
    db: Session = Depends(get_db),
):
    """Attempt to delete a journal entry. Posted entries are read-only and refuse deletion (409 Conflict)."""
    ledger_service.delete_journal_entry(session=db, entry_id=entry_id)
    return {"status": "deleted"}


@router.post("/entries/{entry_id}/reverse", response_model=JournalEntryRead, status_code=status.HTTP_201_CREATED)
def reverse_entry(
    entry_id: str,
    payload: JournalEntryReverseRequest | None = None,
    db: Session = Depends(get_db),
):
    """Create and post a reversing entry that swaps debits and credits of a posted entry."""
    rev_date = payload.reversal_date if payload else None
    desc = payload.description if payload else None
    created_by = payload.created_by if payload else "U-0099"
    return ledger_service.reverse_journal_entry(
        session=db,
        entry_id=entry_id,
        reversal_date=rev_date,
        description=desc,
        created_by=created_by,
    )


@router.post("/post-payroll/{run_id}", response_model=JournalEntryRead, status_code=status.HTTP_201_CREATED)
def post_payroll_run(
    run_id: str,
    db: Session = Depends(get_db),
):
    """Post a payroll run's totals to employer-cost accounts (5001..5005) and payables (2100..2140, 1300)."""
    return ledger_service.post_payroll_run_to_ledger(session=db, run_id=run_id)
