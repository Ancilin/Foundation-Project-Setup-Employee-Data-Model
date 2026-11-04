"""Vendor, Expense Bill, Approval & Payment workflow, Spend Report, Duplicate Detection, and RBAC HTTP routes (LF-11, LF-13)."""

from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.security import ensure_self_or_hr_admin, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.expense import (
    DuplicateCandidateItem,
    DuplicateCheckRequest,
    DuplicateDetectionReportRead,
    ExpenseApproveRequest,
    ExpenseCreateRequest,
    ExpensePaymentRequest,
    ExpenseRead,
    MonthlyReconciliationReportRead,
    SpendReportRead,
    VendorRead,
)
from app.services import expense_service

router = APIRouter(prefix="/expenses", tags=["Vendors & Expense Bills"])


@router.get("/vendors", response_model=list[VendorRead])
def get_vendors(
    _current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
    db: Session = Depends(get_db),
):
    """List all active and inactive vendors."""
    return expense_service.list_vendors(db)


@router.get("/report", response_model=SpendReportRead)
def get_spend_report(
    as_of_date: date | None = Query(default=None, description="Cut-off date (defaults to 2026-09-30)"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Return spend report by vendor, by month, and by vendor & month, reconciled against Accounts Payable (2001)."""
    return expense_service.get_spend_report(db, as_of_date=as_of_date)


@router.get("/reconciliation/monthly", response_model=MonthlyReconciliationReportRead)
def get_monthly_reconciliation(
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Compare monthly expense totals in the database and ledger against expenses.csv."""
    return expense_service.reconcile_monthly_expenses_with_csv(db)


@router.get("/duplicates", response_model=DuplicateDetectionReportRead)
def get_duplicate_bills(
    window_days: int = Query(default=0, ge=0, le=30, description="Date window in days for duplicate detection"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Scan all expense bills to detect likely duplicate bills (same vendor, amount, and date or bill_reference)."""
    return expense_service.detect_duplicate_bills(db, window_days=window_days)


@router.post("/duplicates/check", response_model=list[DuplicateCandidateItem])
def check_duplicate_candidate(
    payload: DuplicateCheckRequest,
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Check whether a candidate expense bill matches any existing bill."""
    return expense_service.find_potential_duplicates_for_bill(
        session=db,
        vendor_id=payload.vendor_id,
        expense_date=payload.expense_date,
        amount_excl_gst=payload.amount_excl_gst,
        total_amount=payload.total_amount,
        bill_reference=payload.bill_reference,
        window_days=payload.window_days,
    )


@router.get("", response_model=list[ExpenseRead])
def list_expense_bills(
    vendor_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    month: str | None = Query(default=None, description="YYYY-MM"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """List expense bills with optional filters for vendor_id, status, and month."""
    return expense_service.list_expenses(
        session=db,
        vendor_id=vendor_id,
        status=status_filter,
        month=month,
    )


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def submit_expense_bill(
    payload: ExpenseCreateRequest,
    current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
    db: Session = Depends(get_db),
):
    """Submit a new vendor expense bill in SUBMITTED status (employees may submit only for their own employee_id)."""
    ensure_self_or_hr_admin(current_user, payload.submitted_by)
    return expense_service.create_expense_bill(
        session=db,
        vendor_id=payload.vendor_id,
        expense_date=payload.expense_date,
        description=payload.description,
        amount_excl_gst=payload.amount_excl_gst,
        submitted_by=payload.submitted_by,
        department_id=payload.department_id,
        category_account=payload.category_account,
        bill_reference=payload.bill_reference,
        gst_rate_percent=payload.gst_rate_percent,
        due_date=payload.due_date,
        expense_id=payload.expense_id,
        allow_duplicate=payload.allow_duplicate,
    )


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense_bill(
    expense_id: str,
    current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
    db: Session = Depends(get_db),
):
    """Retrieve a single expense bill by ID (employees may view only bills they submitted)."""
    bill = expense_service.get_expense(db, expense_id=expense_id)
    ensure_self_or_hr_admin(current_user, bill.submitted_by)
    return bill


@router.post("/{expense_id}/approve", response_model=ExpenseRead)
def approve_bill(
    expense_id: str,
    payload: ExpenseApproveRequest,
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Approve a SUBMITTED expense bill (enforcing separation of duties: approved_by != submitted_by)
    and post it to the ledger (Debit Expense & GST Input 1200, Credit Payable 2001).
    """
    return expense_service.approve_expense_bill(
        session=db,
        expense_id=expense_id,
        approved_by=payload.approved_by,
    )


@router.post("/{expense_id}/pay", response_model=ExpenseRead)
def pay_bill(
    expense_id: str,
    payload: ExpensePaymentRequest,
    _current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Pay an approved expense bill (refuses unapproved bills) and post payment to the ledger
    (Debit Payable 2001, Credit Bank 1001) so the payable is cleared without counting expense twice.
    """
    return expense_service.pay_expense_bill(
        session=db,
        expense_id=expense_id,
        paid_date=payload.paid_date,
        payment_mode=payload.payment_mode,
        paid_by=payload.paid_by,
    )
