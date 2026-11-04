"""Vendor and Expense Bill service (LF-11):
- Bill lifecycle: SUBMITTED -> APPROVED -> PAID (with UNPAID supported for seeded approved-unpaid bills)
- Separation of duties: the person who approves a bill cannot be the person who submitted it
- Guard: a bill cannot be paid before approval
- Double-entry ledger posting on approval:
    Debit 5101..5112 (category_account) for amount_excl_gst
    Debit 1200 (GST Input Credit) for gst_amount (if > 0)
    Credit 2001 (Accounts Payable) for total_amount
- Double-entry ledger posting on payment (clears payable only; never counts expense twice):
    Debit 2001 (Accounts Payable) for total_amount
    Credit 1001 (Bank - Operating Account) for total_amount
- Spend report by vendor, by month, and by vendor & month + reconciliation with Accounts Payable (2001)
- Monthly reconciliation against expenses.csv
- Duplicate bill detector (same vendor + bill_reference, or same vendor + amount + date)
"""

from collections import defaultdict
import csv
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.department import Department
from app.models.expense import Expense, Vendor
from app.models.ledger import JournalEntry, JournalLine
from app.services.ledger_service import account_balance, create_journal_entry, round_money

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_EXPENSES_CSV = ROOT_DIR / "data" / "csv" / "expenses.csv"

POSTED_EXPENSE_STATUSES = ("APPROVED", "UNPAID", "PAID")
OPEN_PAYABLE_STATUSES = ("APPROVED", "UNPAID")


def list_vendors(session: Session) -> list[Vendor]:
    """Return all vendors ordered by vendor_id."""
    return list(session.scalars(select(Vendor).order_by(Vendor.vendor_id)).all())


def get_vendor(session: Session, vendor_id: str) -> Vendor:
    """Return a single vendor or raise NotFoundError."""
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise NotFoundError(f"Vendor '{vendor_id}' not found")
    return vendor


def _next_expense_id(session: Session) -> str:
    count = session.scalar(select(func.count(Expense.expense_id))) or 0
    cand = f"EXP-{count + 1:05d}"
    if session.get(Expense, cand) is not None:
        cand = f"EXP-{uuid.uuid4().hex[:5].upper()}"
    return cand


def get_expense(session: Session, expense_id: str) -> Expense:
    """Retrieve a single expense bill or raise NotFoundError."""
    exp = session.get(Expense, expense_id)
    if not exp:
        raise NotFoundError(f"Expense bill '{expense_id}' not found")
    return exp


def list_expenses(
    session: Session,
    vendor_id: str | None = None,
    status: str | None = None,
    month: str | None = None,
) -> list[Expense]:
    """List expense bills with optional filters for vendor_id, status, and month (YYYY-MM)."""
    stmt = select(Expense).order_by(Expense.expense_date, Expense.expense_id)
    if vendor_id:
        stmt = stmt.where(Expense.vendor_id == vendor_id)
    if status:
        stmt = stmt.where(Expense.status == status.upper())
    rows = list(session.scalars(stmt).all())
    if month:
        rows = [r for r in rows if r.expense_date.isoformat()[:7] == month]
    return rows


def find_potential_duplicates_for_bill(
    session: Session,
    vendor_id: str,
    expense_date: date,
    amount_excl_gst: Decimal | None = None,
    total_amount: Decimal | None = None,
    bill_reference: str | None = None,
    window_days: int = 0,
    exclude_expense_id: str | None = None,
) -> list[dict[str, Any]]:
    """Check existing bills for likely duplicates of a candidate bill.
    Flags a bill as a duplicate if:
    1) Same vendor_id and identical bill_reference (case-insensitive), OR
    2) Same vendor_id, same amount (amount_excl_gst or total_amount), and expense_date within window_days.
    """
    stmt = select(Expense).where(
        Expense.vendor_id == vendor_id,
        Expense.status != "REJECTED",
    )
    existing_bills = list(session.scalars(stmt).all())

    target_excl = round_money(amount_excl_gst) if amount_excl_gst is not None else None
    target_total = round_money(total_amount) if total_amount is not None else None
    target_ref = bill_reference.strip().upper() if bill_reference else None

    candidates: list[dict[str, Any]] = []
    for bill in existing_bills:
        if exclude_expense_id and bill.expense_id == exclude_expense_id:
            continue

        reasons: list[str] = []
        if target_ref and bill.bill_reference and bill.bill_reference.strip().upper() == target_ref:
            reasons.append(f"Same vendor and bill_reference '{bill.bill_reference}'")

        date_diff = abs((bill.expense_date - expense_date).days)
        if date_diff <= window_days:
            amt_match = False
            if target_excl is not None and round_money(bill.amount_excl_gst) == target_excl:
                amt_match = True
            if target_total is not None and round_money(bill.total_amount) == target_total:
                amt_match = True
            if amt_match:
                if date_diff == 0:
                    reasons.append("Same vendor, amount, and expense_date")
                else:
                    reasons.append(f"Same vendor, amount, and expense_date within {date_diff} day(s)")

        if reasons:
            candidates.append(
                {
                    "expense_id": bill.expense_id,
                    "vendor_id": bill.vendor_id,
                    "expense_date": bill.expense_date,
                    "bill_reference": bill.bill_reference,
                    "amount_excl_gst": round_money(bill.amount_excl_gst),
                    "total_amount": round_money(bill.total_amount),
                    "status": bill.status,
                    "reason": "; ".join(reasons),
                }
            )
    return candidates


def detect_duplicate_bills(
    session: Session,
    window_days: int = 0,
) -> dict[str, Any]:
    """Scan all non-rejected expense bills in the database and return likely duplicate pairs."""
    bills = list(
        session.scalars(
            select(Expense)
            .where(Expense.status != "REJECTED")
            .order_by(Expense.vendor_id, Expense.expense_date, Expense.expense_id)
        ).all()
    )

    by_vendor: dict[str, list[Expense]] = defaultdict(list)
    for b in bills:
        by_vendor[b.vendor_id].append(b)

    duplicates: list[dict[str, Any]] = []
    for vid, v_bills in by_vendor.items():
        n = len(v_bills)
        for i in range(n):
            b1 = v_bills[i]
            for j in range(i + 1, n):
                b2 = v_bills[j]
                reasons: list[str] = []
                if (
                    b1.bill_reference
                    and b2.bill_reference
                    and b1.bill_reference.strip().upper() == b2.bill_reference.strip().upper()
                ):
                    reasons.append(f"Identical bill_reference '{b1.bill_reference}'")

                date_diff = abs((b1.expense_date - b2.expense_date).days)
                if date_diff <= window_days and (
                    round_money(b1.total_amount) == round_money(b2.total_amount)
                    or round_money(b1.amount_excl_gst) == round_money(b2.amount_excl_gst)
                ):
                    if date_diff == 0:
                        reasons.append("Same vendor, amount, and expense_date")
                    else:
                        reasons.append(f"Same vendor, amount, and date within {date_diff} day(s)")

                if reasons:
                    duplicates.append(
                        {
                            "first_expense_id": b1.expense_id,
                            "second_expense_id": b2.expense_id,
                            "vendor_id": vid,
                            "expense_date_1": b1.expense_date,
                            "expense_date_2": b2.expense_date,
                            "amount_excl_gst": round_money(b1.amount_excl_gst),
                            "total_amount": round_money(b1.total_amount),
                            "bill_reference_1": b1.bill_reference,
                            "bill_reference_2": b2.bill_reference,
                            "reason": "; ".join(reasons),
                        }
                    )

    return {
        "duplicate_groups_count": len(duplicates),
        "duplicates": duplicates,
    }


def create_expense_bill(
    session: Session,
    vendor_id: str,
    expense_date: date,
    description: str,
    amount_excl_gst: Decimal,
    submitted_by: str,
    department_id: str = "D09",
    category_account: int | None = None,
    bill_reference: str | None = None,
    gst_rate_percent: Decimal = Decimal("18.00"),
    due_date: date | None = None,
    expense_id: str | None = None,
    allow_duplicate: bool = False,
) -> Expense:
    """Record a new vendor expense bill in SUBMITTED status.
    - Does NOT post to the ledger until approved.
    - Checks for duplicate bills unless allow_duplicate=True.
    """
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        raise NotFoundError(f"Vendor '{vendor_id}' not found")

    dept = session.get(Department, department_id)
    if not dept:
        raise NotFoundError(f"Department '{department_id}' not found")

    if not submitted_by or not submitted_by.strip():
        raise ValidationError("submitted_by is required when recording an expense bill.")

    amt_excl = round_money(amount_excl_gst)
    if amt_excl <= Decimal("0.00"):
        raise ValidationError("amount_excl_gst must be greater than zero.")

    gst_rate = round_money(gst_rate_percent)
    if gst_rate < Decimal("0.00"):
        raise ValidationError("gst_rate_percent cannot be negative.")

    gst_amt = round_money(amt_excl * gst_rate / Decimal("100.00"))
    total_amt = round_money(amt_excl + gst_amt)

    final_exp_id = expense_id or _next_expense_id(session)
    if session.get(Expense, final_exp_id) is not None:
        raise ConflictError(f"Expense bill '{final_exp_id}' already exists")

    yymm = f"{str(expense_date.year)[-2:]}{expense_date.month:02d}"
    final_bill_ref = (
        bill_reference.strip()
        if bill_reference and bill_reference.strip()
        else f"BILL-{yymm}-{final_exp_id.split('-')[-1]}"
    )

    if not allow_duplicate:
        dup_matches = find_potential_duplicates_for_bill(
            session=session,
            vendor_id=vendor_id,
            expense_date=expense_date,
            amount_excl_gst=amt_excl,
            total_amount=total_amt,
            bill_reference=final_bill_ref,
            window_days=0,
        )
        if dup_matches:
            dup_ids = ", ".join(m["expense_id"] for m in dup_matches)
            reasons = "; ".join(m["reason"] for m in dup_matches)
            raise ConflictError(
                f"Likely duplicate expense bill detected against existing bill(s) [{dup_ids}]: {reasons}",
                error_code="DUPLICATE_EXPENSE_BILL",
            )

    eff_category = int(category_account or vendor.primary_expense_account)
    eff_due_date = due_date or (expense_date + timedelta(days=int(vendor.payment_terms_days or 30)))

    expense = Expense(
        expense_id=final_exp_id,
        expense_date=expense_date,
        category_account=eff_category,
        vendor_id=vendor_id,
        bill_reference=final_bill_ref,
        description=description.strip(),
        department_id=department_id,
        amount_excl_gst=amt_excl,
        gst_rate_percent=gst_rate,
        gst_amount=gst_amt,
        total_amount=total_amt,
        due_date=eff_due_date,
        paid_date=None,
        status="SUBMITTED",
        payment_mode=None,
        submitted_by=submitted_by.strip(),
        approved_by=None,
        ledger_entry_id=None,
        payment_ledger_entry_id=None,
    )
    session.add(expense)
    session.commit()
    session.refresh(expense)
    return expense


def post_expense_bill_to_ledger(
    session: Session,
    expense_id: str,
    created_by: str = "U-0099",
) -> dict[str, Any]:
    """Post an approved expense bill to the double-entry ledger:
    - Debit category_account (5101..5112) for amount_excl_gst
    - Debit 1200 (GST Input Credit) for gst_amount (if > 0)
    - Credit 2001 (Accounts Payable) for total_amount
    Refuses to post a SUBMITTED or REJECTED bill.
    """
    bill = get_expense(session, expense_id)

    if bill.status in ("SUBMITTED", "REJECTED") or not bill.approved_by:
        raise ValidationError(
            f"Expense bill '{expense_id}' has status '{bill.status}' and cannot be posted before approval.",
            error_code="BILL_NOT_APPROVED",
        )

    if bill.ledger_entry_id:
        existing_je = session.get(JournalEntry, bill.ledger_entry_id)
        if existing_je is not None:
            raise ConflictError(
                f"Expense bill '{expense_id}' is already posted to ledger entry '{bill.ledger_entry_id}'.",
                error_code="ALREADY_POSTED_EXPENSE",
            )

    amt_excl = round_money(bill.amount_excl_gst)
    gst_amt = round_money(bill.gst_amount)
    total_amt = round_money(bill.total_amount)

    lines: list[dict[str, Any]] = [
        {
            "account_code": int(bill.category_account),
            "debit": amt_excl,
            "credit": Decimal("0.00"),
            "cost_center_department_id": bill.department_id,
            "line_description": bill.description,
        }
    ]
    if gst_amt > Decimal("0.00"):
        lines.append(
            {
                "account_code": 1200,
                "debit": gst_amt,
                "credit": Decimal("0.00"),
                "cost_center_department_id": None,
                "line_description": "GST input credit",
            }
        )
    lines.append(
        {
            "account_code": 2001,
            "debit": Decimal("0.00"),
            "credit": total_amt,
            "cost_center_department_id": None,
            "line_description": f"Payable {bill.bill_reference}",
        }
    )

    je = create_journal_entry(
        session=session,
        lines=lines,
        entry_date=bill.expense_date,
        description=f"Expense bill {bill.bill_reference}",
        source_type="EXPENSE",
        source_id=bill.expense_id,
        created_by=created_by,
    )
    bill.ledger_entry_id = je["entry_id"]
    session.commit()
    session.refresh(bill)
    return je


def approve_expense_bill(
    session: Session,
    expense_id: str,
    approved_by: str,
) -> Expense:
    """Approve a SUBMITTED expense bill and post it to the ledger.
    Enforces separation of duties: approved_by cannot equal submitted_by.
    """
    bill = get_expense(session, expense_id)

    if not approved_by or not approved_by.strip():
        raise ValidationError("approved_by is required to approve an expense bill.")

    clean_approver = approved_by.strip()
    clean_submitter = (bill.submitted_by or "").strip()

    if clean_approver.upper() == clean_submitter.upper():
        raise ValidationError(
            f"Separation of duties violation: submitter '{clean_submitter}' cannot approve their own expense bill '{expense_id}'.",
            error_code="SEPARATION_OF_DUTIES_VIOLATION",
        )

    if bill.status in ("APPROVED", "UNPAID", "PAID"):
        raise ConflictError(
            f"Expense bill '{expense_id}' is already approved (status={bill.status}).",
            error_code="BILL_ALREADY_APPROVED",
        )
    if bill.status != "SUBMITTED":
        raise ValidationError(
            f"Only SUBMITTED bills can be approved (current status: {bill.status}).",
            error_code="INVALID_BILL_STATUS",
        )

    bill.approved_by = clean_approver
    bill.status = "APPROVED"
    session.flush()

    post_expense_bill_to_ledger(session, expense_id=bill.expense_id, created_by=clean_approver)
    session.refresh(bill)
    return bill


def pay_expense_bill(
    session: Session,
    expense_id: str,
    paid_date: date,
    payment_mode: str = "NEFT",
    paid_by: str | None = "U-0099",
) -> Expense:
    """Pay an approved expense bill and post the payment to the ledger.
    - Guard: A bill cannot be paid before approval.
    - Guard: A bill cannot be paid twice.
    - Ledger posting debits 2001 (Accounts Payable) and credits 1001 (Bank), clearing the payable
      without counting the expense a second time.
    """
    bill = get_expense(session, expense_id)

    if bill.status == "SUBMITTED" or not bill.approved_by or not bill.ledger_entry_id:
        raise ValidationError(
            f"Expense bill '{expense_id}' cannot be paid before approval (current status: {bill.status}).",
            error_code="BILL_NOT_APPROVED",
        )

    if bill.status == "PAID" or bill.payment_ledger_entry_id is not None:
        raise ConflictError(
            f"Expense bill '{expense_id}' is already paid (payment_ledger_entry_id={bill.payment_ledger_entry_id}).",
            error_code="BILL_ALREADY_PAID",
        )

    if bill.status not in ("APPROVED", "UNPAID"):
        raise ValidationError(
            f"Expense bill '{expense_id}' in status '{bill.status}' cannot be paid.",
            error_code="INVALID_BILL_STATUS",
        )

    total_amt = round_money(bill.total_amount)
    je = create_journal_entry(
        session=session,
        lines=[
            {
                "account_code": 2001,
                "debit": total_amt,
                "credit": Decimal("0.00"),
                "cost_center_department_id": None,
                "line_description": "Payable cleared",
            },
            {
                "account_code": 1001,
                "debit": Decimal("0.00"),
                "credit": total_amt,
                "cost_center_department_id": None,
                "line_description": "Bank payment",
            },
        ],
        entry_date=paid_date,
        description=f"Vendor payment {bill.bill_reference}",
        source_type="EXPENSE_PAYMENT",
        source_id=bill.expense_id,
        created_by=paid_by or "U-0099",
    )

    bill.paid_date = paid_date
    bill.payment_mode = payment_mode.strip() if payment_mode else "NEFT"
    bill.status = "PAID"
    bill.payment_ledger_entry_id = je["entry_id"]
    session.commit()
    session.refresh(bill)
    return bill


def get_spend_report(
    session: Session,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Generate a spend report by vendor, by month, and by vendor & month,
    and reconcile unpaid approved bills against Accounts Payable (account 2001).
    """
    eff_date = as_of_date or date(2026, 9, 30)
    vendors = {v.vendor_id: v for v in list_vendors(session)}

    bills = list(
        session.scalars(
            select(Expense)
            .where(
                Expense.status.in_(POSTED_EXPENSE_STATUSES),
                Expense.expense_date <= eff_date,
            )
            .order_by(Expense.expense_date, Expense.expense_id)
        ).all()
    )

    vendor_agg: dict[str, dict[str, Any]] = {}
    for vid, v in vendors.items():
        vendor_agg[vid] = {
            "vendor_id": vid,
            "vendor_name": v.vendor_name,
            "primary_expense_account": v.primary_expense_account,
            "bills_count": 0,
            "amount_excl_gst": Decimal("0.00"),
            "gst_amount": Decimal("0.00"),
            "total_amount": Decimal("0.00"),
            "paid_amount": Decimal("0.00"),
            "unpaid_amount": Decimal("0.00"),
        }

    month_agg: dict[str, dict[str, Any]] = {}
    vendor_month_agg: dict[tuple[str, str], dict[str, Any]] = {}

    total_excl = Decimal("0.00")
    total_gst = Decimal("0.00")
    total_spend = Decimal("0.00")
    total_paid = Decimal("0.00")
    total_unpaid = Decimal("0.00")

    for b in bills:
        amt_excl = round_money(b.amount_excl_gst)
        gst_amt = round_money(b.gst_amount)
        tot_amt = round_money(b.total_amount)
        is_paid_as_of = b.status == "PAID" and (b.paid_date is None or b.paid_date <= eff_date)

        paid_val = tot_amt if is_paid_as_of else Decimal("0.00")
        unpaid_val = Decimal("0.00") if is_paid_as_of else tot_amt

        total_excl = round_money(total_excl + amt_excl)
        total_gst = round_money(total_gst + gst_amt)
        total_spend = round_money(total_spend + tot_amt)
        total_paid = round_money(total_paid + paid_val)
        total_unpaid = round_money(total_unpaid + unpaid_val)

        # Vendor aggregation
        v_entry = vendor_agg.get(b.vendor_id)
        if v_entry is not None:
            v_entry["bills_count"] += 1
            v_entry["amount_excl_gst"] = round_money(v_entry["amount_excl_gst"] + amt_excl)
            v_entry["gst_amount"] = round_money(v_entry["gst_amount"] + gst_amt)
            v_entry["total_amount"] = round_money(v_entry["total_amount"] + tot_amt)
            v_entry["paid_amount"] = round_money(v_entry["paid_amount"] + paid_val)
            v_entry["unpaid_amount"] = round_money(v_entry["unpaid_amount"] + unpaid_val)

        # Month aggregation
        ym = b.expense_date.isoformat()[:7]
        if ym not in month_agg:
            month_agg[ym] = {
                "month": ym,
                "bills_count": 0,
                "amount_excl_gst": Decimal("0.00"),
                "gst_amount": Decimal("0.00"),
                "total_amount": Decimal("0.00"),
                "paid_amount": Decimal("0.00"),
                "unpaid_amount": Decimal("0.00"),
            }
        m_entry = month_agg[ym]
        m_entry["bills_count"] += 1
        m_entry["amount_excl_gst"] = round_money(m_entry["amount_excl_gst"] + amt_excl)
        m_entry["gst_amount"] = round_money(m_entry["gst_amount"] + gst_amt)
        m_entry["total_amount"] = round_money(m_entry["total_amount"] + tot_amt)
        m_entry["paid_amount"] = round_money(m_entry["paid_amount"] + paid_val)
        m_entry["unpaid_amount"] = round_money(m_entry["unpaid_amount"] + unpaid_val)

        # Vendor-Month aggregation
        vm_key = (ym, b.vendor_id)
        if vm_key not in vendor_month_agg:
            v_name = vendors[b.vendor_id].vendor_name if b.vendor_id in vendors else b.vendor_id
            vendor_month_agg[vm_key] = {
                "month": ym,
                "vendor_id": b.vendor_id,
                "vendor_name": v_name,
                "bills_count": 0,
                "amount_excl_gst": Decimal("0.00"),
                "gst_amount": Decimal("0.00"),
                "total_amount": Decimal("0.00"),
            }
        vm_entry = vendor_month_agg[vm_key]
        vm_entry["bills_count"] += 1
        vm_entry["amount_excl_gst"] = round_money(vm_entry["amount_excl_gst"] + amt_excl)
        vm_entry["gst_amount"] = round_money(vm_entry["gst_amount"] + gst_amt)
        vm_entry["total_amount"] = round_money(vm_entry["total_amount"] + tot_amt)

    ap_bal_info = account_balance(session, 2001, as_of_date=eff_date)
    ap_balance = round_money(ap_bal_info["balance"])
    ap_diff = round_money(ap_balance - total_unpaid)

    return {
        "total_bills": len(bills),
        "total_amount_excl_gst": total_excl,
        "total_gst_amount": total_gst,
        "total_spend_amount": total_spend,
        "total_paid_amount": total_paid,
        "total_unpaid_payable": total_unpaid,
        "ledger_account_2001_balance": ap_balance,
        "payable_reconciled_difference": ap_diff,
        "is_payable_reconciled": abs(ap_diff) == Decimal("0.00"),
        "by_vendor": [v for v in vendor_agg.values() if v["bills_count"] > 0],
        "by_month": [month_agg[k] for k in sorted(month_agg.keys())],
        "by_vendor_month": [vendor_month_agg[k] for k in sorted(vendor_month_agg.keys())],
    }


def reconcile_monthly_expenses_with_csv(
    session: Session,
    csv_path: Path | None = None,
) -> dict[str, Any]:
    """Compare monthly expense totals from the database and the ledger (5101..5112)
    with the official expenses.csv file.
    """
    target_csv = csv_path or DEFAULT_EXPENSES_CSV
    if not target_csv.exists():
        raise NotFoundError(f"Expenses CSV not found at '{target_csv}'")

    # 1. Read official CSV monthly totals
    csv_monthly: dict[str, dict[str, Any]] = {}
    with target_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ym = str(row["expense_date"]).strip()[:7]
            if ym not in csv_monthly:
                csv_monthly[ym] = {
                    "count": 0,
                    "excl": Decimal("0.00"),
                    "gst": Decimal("0.00"),
                    "total": Decimal("0.00"),
                }
            csv_monthly[ym]["count"] += 1
            csv_monthly[ym]["excl"] = round_money(csv_monthly[ym]["excl"] + Decimal(str(row["amount_excl_gst"])))
            csv_monthly[ym]["gst"] = round_money(csv_monthly[ym]["gst"] + Decimal(str(row["gst_amount"])))
            csv_monthly[ym]["total"] = round_money(csv_monthly[ym]["total"] + Decimal(str(row["total_amount"])))

    # 2. Read DB Expense table monthly totals (approved/paid bills)
    db_bills = list(
        session.scalars(
            select(Expense).where(Expense.status.in_(POSTED_EXPENSE_STATUSES))
        ).all()
    )
    db_monthly: dict[str, dict[str, Any]] = {}
    for b in db_bills:
        ym = b.expense_date.isoformat()[:7]
        if ym not in db_monthly:
            db_monthly[ym] = {
                "count": 0,
                "excl": Decimal("0.00"),
                "gst": Decimal("0.00"),
                "total": Decimal("0.00"),
            }
        db_monthly[ym]["count"] += 1
        db_monthly[ym]["excl"] = round_money(db_monthly[ym]["excl"] + round_money(b.amount_excl_gst))
        db_monthly[ym]["gst"] = round_money(db_monthly[ym]["gst"] + round_money(b.gst_amount))
        db_monthly[ym]["total"] = round_money(db_monthly[ym]["total"] + round_money(b.total_amount))

    # 3. Read Ledger expense debits (accounts 5101..5112 where source_type == 'EXPENSE')
    stmt_jl = (
        select(JournalEntry.posting_period, func.coalesce(func.sum(JournalLine.debit), 0))
        .join(JournalLine, JournalLine.entry_id == JournalEntry.entry_id)
        .where(
            JournalEntry.source_type == "EXPENSE",
            JournalLine.account_code.between(5101, 5112),
        )
        .group_by(JournalEntry.posting_period)
    )
    ledger_monthly: dict[str, Decimal] = {}
    for period, debit_sum in session.execute(stmt_jl).all():
        ledger_monthly[str(period)] = round_money(debit_sum)

    all_months = sorted(set(csv_monthly.keys()) | set(db_monthly.keys()))
    month_rows: list[dict[str, Any]] = []

    tot_db_excl = Decimal("0.00")
    tot_csv_excl = Decimal("0.00")
    tot_ledger_dr = Decimal("0.00")
    tot_db_total = Decimal("0.00")
    tot_csv_total = Decimal("0.00")
    max_diff = Decimal("0.00")
    all_match = True

    for ym in all_months:
        c_info = csv_monthly.get(
            ym,
            {"count": 0, "excl": Decimal("0.00"), "gst": Decimal("0.00"), "total": Decimal("0.00")},
        )
        d_info = db_monthly.get(
            ym,
            {"count": 0, "excl": Decimal("0.00"), "gst": Decimal("0.00"), "total": Decimal("0.00")},
        )
        l_dr = ledger_monthly.get(ym, Decimal("0.00"))

        diff_excl = round_money(d_info["excl"] - c_info["excl"])
        diff_total = round_money(d_info["total"] - c_info["total"])
        diff_ledger = round_money(l_dr - c_info["excl"])
        row_matches = (
            diff_excl == Decimal("0.00")
            and diff_total == Decimal("0.00")
            and diff_ledger == Decimal("0.00")
        )
        if not row_matches:
            all_match = False

        max_diff = max(max_diff, abs(diff_excl), abs(diff_total), abs(diff_ledger))

        tot_db_excl = round_money(tot_db_excl + d_info["excl"])
        tot_csv_excl = round_money(tot_csv_excl + c_info["excl"])
        tot_ledger_dr = round_money(tot_ledger_dr + l_dr)
        tot_db_total = round_money(tot_db_total + d_info["total"])
        tot_csv_total = round_money(tot_csv_total + c_info["total"])

        month_rows.append(
            {
                "month": ym,
                "db_bills_count": d_info["count"],
                "csv_bills_count": c_info["count"],
                "db_amount_excl_gst": d_info["excl"],
                "csv_amount_excl_gst": c_info["excl"],
                "ledger_expense_debit": l_dr,
                "db_gst_amount": d_info["gst"],
                "csv_gst_amount": c_info["gst"],
                "db_total_amount": d_info["total"],
                "csv_total_amount": c_info["total"],
                "difference_excl_gst": diff_excl,
                "difference_total": diff_total,
                "matches": row_matches,
            }
        )

    return {
        "total_months": len(month_rows),
        "all_months_match": all_match,
        "total_db_amount_excl_gst": tot_db_excl,
        "total_csv_amount_excl_gst": tot_csv_excl,
        "total_ledger_expense_debit": tot_ledger_dr,
        "total_db_total_amount": tot_db_total,
        "total_csv_total_amount": tot_csv_total,
        "max_monthly_difference": max_diff,
        "months": month_rows,
    }
