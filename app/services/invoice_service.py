"""Invoice, Client, Payment, and Accounts Receivable service (LF-10):
- Invoice status flow: DRAFT -> SENT -> PARTIALLY_PAID -> PAID / OVERDUE / CANCELLED
- GST calculation (18% domestic, 0% export)
- Automatic double-entry ledger postings (Debit 1100 Receivable / Credit 400x Revenue & 2200 GST; Payment Debits 1001 Bank / Credits 1100 Receivable)
- Strict guard: DRAFT and CANCELLED invoices never post to the ledger
- Cancelling a SENT invoice posts a reversing entry to keep ledger 1100 reconciled with open invoices
- Receivables list & reconciliation against ledger account 1100
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.invoice import Client, Invoice, InvoiceItem, InvoicePayment
from app.services.ledger_service import (
    account_balance,
    create_journal_entry,
    reverse_journal_entry,
    round_money,
)

OPEN_INVOICE_STATUSES = ("SENT", "OVERDUE", "PARTIALLY_PAID")


def list_clients(session: Session) -> list[Client]:
    """Return all clients ordered by client_id."""
    return list(session.scalars(select(Client).order_by(Client.client_id)).all())


def _next_invoice_id(session: Session) -> str:
    count = session.scalar(select(func.count(Invoice.invoice_id))) or 0
    cand = f"INV-{count + 1:05d}"
    if session.get(Invoice, cand) is not None:
        cand = f"INV-{uuid.uuid4().hex[:5].upper()}"
    return cand


def _next_invoice_item_base(session: Session) -> int:
    return (session.scalar(select(func.count(InvoiceItem.invoice_item_id))) or 0) + 1


def _next_payment_id(session: Session) -> str:
    count = session.scalar(select(func.count(InvoicePayment.payment_id))) or 0
    cand = f"PAY-{count + 1:05d}"
    if session.get(InvoicePayment, cand) is not None:
        cand = f"PAY-{uuid.uuid4().hex[:5].upper()}"
    return cand


def get_invoice_with_details(session: Session, invoice_id: str) -> dict[str, Any]:
    """Retrieve an invoice with its line items and payment records."""
    inv = session.get(Invoice, invoice_id)
    if not inv:
        raise NotFoundError(f"Invoice '{invoice_id}' not found")

    items = list(
        session.scalars(
            select(InvoiceItem)
            .where(InvoiceItem.invoice_id == invoice_id)
            .order_by(InvoiceItem.line_no)
        ).all()
    )
    payments = list(
        session.scalars(
            select(InvoicePayment)
            .where(InvoicePayment.invoice_id == invoice_id)
            .order_by(InvoicePayment.payment_date, InvoicePayment.payment_id)
        ).all()
    )

    return {
        "invoice_id": inv.invoice_id,
        "invoice_number": inv.invoice_number,
        "client_id": inv.client_id,
        "invoice_date": inv.invoice_date,
        "due_date": inv.due_date,
        "service_line_account": inv.service_line_account,
        "currency": inv.currency,
        "subtotal": round_money(inv.subtotal),
        "gst_rate_percent": round_money(inv.gst_rate_percent),
        "gst_amount": round_money(inv.gst_amount),
        "total_amount": round_money(inv.total_amount),
        "amount_paid": round_money(inv.amount_paid),
        "balance_due": round_money(inv.balance_due),
        "status": inv.status,
        "last_payment_date": inv.last_payment_date,
        "po_number": inv.po_number,
        "carried_in_from_prior_period": inv.carried_in_from_prior_period,
        "created_by": inv.created_by,
        "created_at": inv.created_at,
        "ledger_entry_id": inv.ledger_entry_id,
        "items": items,
        "payments": payments,
    }


def create_invoice(
    session: Session,
    client_id: str,
    invoice_date: date,
    items: list[dict[str, Any] | Any],
    due_date: date | None = None,
    invoice_id: str | None = None,
    invoice_number: str | None = None,
    service_line_account: int | None = None,
    gst_rate_percent: Decimal | None = None,
    po_number: str | None = None,
    created_by: str | None = "U-0099",
) -> dict[str, Any]:
    """Create a new invoice in DRAFT status.
    Draft invoices never post to the ledger until they are sent.
    """
    client = session.get(Client, client_id)
    if not client:
        raise NotFoundError(f"Client '{client_id}' not found")

    if not items:
        raise ValidationError("An invoice requires at least one line item.")

    eff_service_acct = service_line_account or client.primary_service_line
    eff_due_date = due_date or (invoice_date + timedelta(days=int(client.payment_terms_days or 30)))

    if gst_rate_percent is not None:
        eff_gst_rate = round_money(gst_rate_percent)
    else:
        eff_gst_rate = Decimal("18.00") if client.client_type.upper() == "DOMESTIC" else Decimal("0.00")

    final_inv_id = invoice_id or _next_invoice_id(session)
    if session.get(Invoice, final_inv_id) is not None:
        raise ConflictError(f"Invoice '{final_inv_id}' already exists")

    fy = (
        f"{invoice_date.year}-{str(invoice_date.year + 1)[-2:]}"
        if invoice_date.month >= 4
        else f"{invoice_date.year - 1}-{str(invoice_date.year)[-2:]}"
    )
    final_inv_number = invoice_number or f"INV/{fy}/{final_inv_id.split('-')[-1]}"

    subtotal = Decimal("0.00")
    normalized_items: list[dict[str, Any]] = []
    for idx, raw_item in enumerate(items, start=1):
        item_dict = raw_item.model_dump() if hasattr(raw_item, "model_dump") else dict(raw_item)
        qty = round_money(item_dict.get("quantity", Decimal("1.00")))
        uprice = round_money(item_dict["unit_price"])
        amt = round_money(item_dict.get("amount", qty * uprice))
        rev_acct = int(item_dict.get("revenue_account") or eff_service_acct)
        subtotal = round_money(subtotal + amt)
        normalized_items.append(
            {
                "line_no": idx,
                "description": str(item_dict["description"]).strip(),
                "quantity": qty,
                "unit_price": uprice,
                "amount": amt,
                "revenue_account": rev_acct,
            }
        )

    gst_amount = round_money(subtotal * eff_gst_rate / Decimal("100"))
    total_amount = round_money(subtotal + gst_amount)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    inv = Invoice(
        invoice_id=final_inv_id,
        invoice_number=final_inv_number,
        client_id=client_id,
        invoice_date=invoice_date,
        due_date=eff_due_date,
        service_line_account=eff_service_acct,
        currency="INR",
        subtotal=subtotal,
        gst_rate_percent=eff_gst_rate,
        gst_amount=gst_amount,
        total_amount=total_amount,
        amount_paid=Decimal("0.00"),
        balance_due=total_amount,
        status="DRAFT",
        last_payment_date=None,
        po_number=po_number,
        carried_in_from_prior_period="N",
        created_by=created_by,
        created_at=now_str,
        ledger_entry_id=None,
    )
    session.add(inv)

    item_base = _next_invoice_item_base(session)
    for offset, ni in enumerate(normalized_items):
        ii_id = f"II-{item_base + offset:06d}"
        if session.get(InvoiceItem, ii_id) is not None:
            ii_id = f"II-{uuid.uuid4().hex[:6].upper()}"
        session.add(
            InvoiceItem(
                invoice_item_id=ii_id,
                invoice_id=final_inv_id,
                line_no=ni["line_no"],
                description=ni["description"],
                quantity=ni["quantity"],
                unit_price=ni["unit_price"],
                amount=ni["amount"],
                revenue_account=ni["revenue_account"],
            )
        )

    session.commit()
    return get_invoice_with_details(session, final_inv_id)


def post_invoice_to_ledger(session: Session, invoice_id: str) -> dict[str, Any]:
    """Post an issued invoice to the double-entry ledger:
    - Debit 1100 (Accounts Receivable): total_amount
    - Credit 400x (Service Line Revenue): subtotal
    - Credit 2200 (GST Output Payable): gst_amount (when > 0)
    Refuses to post DRAFT or CANCELLED invoices.
    """
    inv = session.get(Invoice, invoice_id)
    if not inv:
        raise NotFoundError(f"Invoice '{invoice_id}' not found")

    if inv.status in ("DRAFT", "CANCELLED"):
        raise ValidationError(
            f"Invoice '{invoice_id}' has status '{inv.status}'. "
            "DRAFT and CANCELLED invoices must never be posted to the ledger.",
            error_code="INVALID_INVOICE_STATUS_FOR_POSTING",
        )

    if inv.ledger_entry_id:
        return get_invoice_with_details(session, invoice_id)

    client = session.get(Client, inv.client_id)
    client_name = client.client_name if client else inv.client_id

    lines: list[dict[str, Any]] = [
        {
            "account_code": 1100,
            "debit": round_money(inv.total_amount),
            "credit": Decimal("0.00"),
            "line_description": f"Receivable {inv.invoice_number}",
        },
        {
            "account_code": int(inv.service_line_account),
            "debit": Decimal("0.00"),
            "credit": round_money(inv.subtotal),
            "line_description": f"Revenue {inv.invoice_number}",
        },
    ]
    if round_money(inv.gst_amount) > Decimal("0.00"):
        lines.append(
            {
                "account_code": 2200,
                "debit": Decimal("0.00"),
                "credit": round_money(inv.gst_amount),
                "line_description": f"GST output {inv.invoice_number}",
            }
        )

    entry = create_journal_entry(
        session=session,
        lines=lines,
        entry_date=inv.invoice_date,
        description=f"Invoice {inv.invoice_number} - {client_name}",
        source_type="INVOICE",
        source_id=inv.invoice_id,
        created_by=inv.created_by or "U-0099",
    )
    inv.ledger_entry_id = entry["entry_id"]
    session.commit()
    return get_invoice_with_details(session, invoice_id)


def send_invoice(session: Session, invoice_id: str) -> dict[str, Any]:
    """Transition a DRAFT invoice to SENT and post it to the double-entry ledger."""
    inv = session.get(Invoice, invoice_id)
    if not inv:
        raise NotFoundError(f"Invoice '{invoice_id}' not found")

    if inv.status == "CANCELLED":
        raise ConflictError(f"Cancelled invoice '{invoice_id}' cannot be sent.")
    if inv.status != "DRAFT":
        raise ConflictError(f"Invoice '{invoice_id}' is already '{inv.status}' (only DRAFT invoices can be sent).")

    inv.status = "SENT"
    session.commit()
    return post_invoice_to_ledger(session, invoice_id)


def record_payment(
    session: Session,
    invoice_id: str,
    payment_date: date,
    amount: Decimal,
    payment_mode: str = "NEFT",
    reference_no: str | None = None,
    received_by: str | None = "U-0099",
    payment_id: str | None = None,
) -> dict[str, Any]:
    """Record a customer payment against an open invoice and post to the ledger:
    - Debit 1001 (Bank - Operating Account): amount
    - Credit 1100 (Accounts Receivable): amount
    Updates invoice amount_paid, balance_due, and status (PARTIALLY_PAID or PAID).
    """
    inv = session.get(Invoice, invoice_id)
    if not inv:
        raise NotFoundError(f"Invoice '{invoice_id}' not found")

    if inv.status in ("DRAFT", "CANCELLED"):
        raise ConflictError(
            f"Cannot record payment on '{inv.status}' invoice '{invoice_id}'. Invoice must be SENT first.",
            error_code="INVALID_INVOICE_STATUS",
        )
    if inv.status == "PAID" or round_money(inv.balance_due) <= Decimal("0.00"):
        raise ConflictError(f"Invoice '{invoice_id}' is already fully PAID.")

    pay_amt = round_money(amount)
    if pay_amt <= Decimal("0.00"):
        raise ValidationError("Payment amount must be greater than 0.00.")

    curr_balance = round_money(inv.balance_due)
    if pay_amt > curr_balance:
        raise ValidationError(
            f"Payment amount ({pay_amt}) exceeds invoice balance_due ({curr_balance}).",
            error_code="OVERPAYMENT_NOT_ALLOWED",
        )

    final_pay_id = payment_id or _next_payment_id(session)
    utr_ref = reference_no or f"UTR{uuid.uuid4().int % 10_000_000_000:010d}"

    # Post payment journal entry: Debit 1001 Bank, Credit 1100 Accounts Receivable
    je = create_journal_entry(
        session=session,
        lines=[
            {
                "account_code": 1001,
                "debit": pay_amt,
                "credit": Decimal("0.00"),
                "line_description": f"Bank receipt {utr_ref}",
            },
            {
                "account_code": 1100,
                "debit": Decimal("0.00"),
                "credit": pay_amt,
                "line_description": "Receivable cleared",
            },
        ],
        entry_date=payment_date,
        description=f"Receipt against {inv.invoice_number}",
        source_type="INVOICE_PAYMENT",
        source_id=final_pay_id,
        created_by=received_by or "U-0099",
    )

    payment = InvoicePayment(
        payment_id=final_pay_id,
        invoice_id=inv.invoice_id,
        payment_date=payment_date,
        amount=pay_amt,
        payment_mode=payment_mode,
        reference_no=utr_ref,
        received_by=received_by,
        ledger_entry_id=je["entry_id"],
    )
    session.add(payment)

    inv.amount_paid = round_money(round_money(inv.amount_paid) + pay_amt)
    inv.balance_due = round_money(round_money(inv.total_amount) - inv.amount_paid)
    inv.last_payment_date = payment_date
    inv.status = "PAID" if inv.balance_due == Decimal("0.00") else "PARTIALLY_PAID"

    session.commit()
    return get_invoice_with_details(session, invoice_id)


def mark_invoice_overdue(
    session: Session,
    invoice_id: str,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Mark a SENT invoice as OVERDUE when its due_date has passed and balance_due > 0."""
    inv = session.get(Invoice, invoice_id)
    if not inv:
        raise NotFoundError(f"Invoice '{invoice_id}' not found")

    eff_date = as_of_date or date.today()
    if inv.status not in ("SENT", "PARTIALLY_PAID", "OVERDUE"):
        raise ConflictError(f"Cannot mark invoice with status '{inv.status}' as OVERDUE.")
    if inv.due_date >= eff_date:
        raise ValidationError(f"Invoice '{invoice_id}' is not yet past due_date ({inv.due_date}).")

    inv.status = "OVERDUE"
    session.commit()
    return get_invoice_with_details(session, invoice_id)


def cancel_invoice(
    session: Session,
    invoice_id: str,
    cancel_date: date | None = None,
    cancelled_by: str | None = "U-0099",
) -> dict[str, Any]:
    """Cancel an invoice:
    - If DRAFT: sets status='CANCELLED', balance_due=0.00 without posting anything to the ledger.
    - If SENT or OVERDUE (with amount_paid == 0): sets status='CANCELLED', balance_due=0.00,
      and posts a reversing journal entry so ledger account 1100 stays equal to open invoices.
    - If payments have already been received (amount_paid > 0): refuses cancellation (409 Conflict).
    """
    inv = session.get(Invoice, invoice_id)
    if not inv:
        raise NotFoundError(f"Invoice '{invoice_id}' not found")

    if inv.status == "CANCELLED":
        return get_invoice_with_details(session, invoice_id)

    if round_money(inv.amount_paid) > Decimal("0.00"):
        raise ConflictError(
            f"Invoice '{invoice_id}' has received payments ({inv.amount_paid}) and cannot be cancelled directly.",
            error_code="CANNOT_CANCEL_PAID_INVOICE",
        )

    if inv.status in ("SENT", "OVERDUE") and inv.ledger_entry_id:
        reverse_journal_entry(
            session=session,
            entry_id=inv.ledger_entry_id,
            reversal_date=cancel_date or date.today(),
            description=f"Cancellation reversal of Invoice {inv.invoice_number} ({inv.invoice_id})",
            created_by=cancelled_by,
        )

    inv.status = "CANCELLED"
    inv.balance_due = Decimal("0.00")
    session.commit()
    return get_invoice_with_details(session, invoice_id)


def get_receivables_report(
    session: Session,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Build the Accounts Receivable list (who owes what across open invoices: SENT, OVERDUE, PARTIALLY_PAID)
    and reconcile the total against ledger account 1100.
    """
    eff_date = as_of_date or date(2026, 9, 30)

    open_invs = list(
        session.scalars(
            select(Invoice).where(Invoice.status.in_(OPEN_INVOICE_STATUSES))
        ).all()
    )
    clients_map = {c.client_id: c for c in session.scalars(select(Client)).all()}

    by_client: dict[str, dict[str, Any]] = {}
    for inv in open_invs:
        cid = inv.client_id
        c_obj = clients_map.get(cid)
        if cid not in by_client:
            by_client[cid] = {
                "client_id": cid,
                "client_name": c_obj.client_name if c_obj else cid,
                "client_type": c_obj.client_type if c_obj else "DOMESTIC",
                "open_invoices_count": 0,
                "total_invoiced_open": Decimal("0.00"),
                "total_paid_on_open": Decimal("0.00"),
                "balance_due": Decimal("0.00"),
            }
        by_client[cid]["open_invoices_count"] += 1
        by_client[cid]["total_invoiced_open"] = round_money(
            by_client[cid]["total_invoiced_open"] + round_money(inv.total_amount)
        )
        by_client[cid]["total_paid_on_open"] = round_money(
            by_client[cid]["total_paid_on_open"] + round_money(inv.amount_paid)
        )
        by_client[cid]["balance_due"] = round_money(
            by_client[cid]["balance_due"] + round_money(inv.balance_due)
        )

    client_list = sorted(by_client.values(), key=lambda x: (-x["balance_due"], x["client_id"]))
    total_open_ar = round_money(sum((c["balance_due"] for c in client_list), Decimal("0.00")))

    acct_1100 = account_balance(session, account_code=1100, as_of_date=eff_date)
    ledger_1100_bal = round_money(acct_1100["balance"])
    diff = round_money(ledger_1100_bal - total_open_ar)

    return {
        "as_of_date": eff_date,
        "total_open_invoices": len(open_invs),
        "total_open_receivables": total_open_ar,
        "ledger_account_1100_balance": ledger_1100_bal,
        "reconciled_difference": diff,
        "is_reconciled": abs(diff) <= Decimal("0.01"),
        "clients": client_list,
    }
