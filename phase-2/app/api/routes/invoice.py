"""Client, Invoice, Payment, and Accounts Receivable HTTP routes (LF-10)."""

from datetime import date
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.invoice import (
    ClientRead,
    InvoiceCreateRequest,
    InvoicePaymentCreateRequest,
    InvoiceRead,
    ReceivablesReportRead,
)
from app.services import invoice_service

router = APIRouter(prefix="/invoices", tags=["Invoices & Receivables"])


@router.get("/clients", response_model=list[ClientRead])
def get_clients(db: Session = Depends(get_db)):
    """List all domestic and export clients."""
    return invoice_service.list_clients(db)


@router.get("/receivables", response_model=ReceivablesReportRead)
def get_receivables(
    as_of_date: date | None = Query(default=None, description="Reconciliation date (defaults to 2026-09-30)"),
    db: Session = Depends(get_db),
):
    """Return the Accounts Receivable list (who owes what) reconciled against ledger account 1100."""
    return invoice_service.get_receivables_report(db, as_of_date=as_of_date)


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_draft_invoice(
    payload: InvoiceCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a new invoice in DRAFT status (never posts to the ledger while in DRAFT)."""
    return invoice_service.create_invoice(
        session=db,
        client_id=payload.client_id,
        invoice_date=payload.invoice_date,
        items=payload.items,
        due_date=payload.due_date,
        invoice_id=payload.invoice_id,
        invoice_number=payload.invoice_number,
        service_line_account=payload.service_line_account,
        gst_rate_percent=payload.gst_rate_percent,
        po_number=payload.po_number,
        created_by=payload.created_by,
    )


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve an invoice with its line items and payments."""
    return invoice_service.get_invoice_with_details(db, invoice_id=invoice_id)


@router.post("/{invoice_id}/send", response_model=InvoiceRead)
def send_draft_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
):
    """Transition a DRAFT invoice to SENT and post Receivable (1100), Revenue (400x), and GST (2200) to the ledger."""
    return invoice_service.send_invoice(db, invoice_id=invoice_id)


@router.post("/{invoice_id}/post", response_model=InvoiceRead)
def post_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
):
    """Attempt to post an invoice to the ledger. Refuses DRAFT and CANCELLED invoices."""
    return invoice_service.post_invoice_to_ledger(db, invoice_id=invoice_id)


@router.post("/{invoice_id}/payments", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def record_invoice_payment(
    invoice_id: str,
    payload: InvoicePaymentCreateRequest,
    db: Session = Depends(get_db),
):
    """Record a payment against an open invoice, reducing balance_due and debiting Bank (1001) / crediting Receivable (1100)."""
    return invoice_service.record_payment(
        session=db,
        invoice_id=invoice_id,
        payment_date=payload.payment_date,
        amount=payload.amount,
        payment_mode=payload.payment_mode,
        reference_no=payload.reference_no,
        received_by=payload.received_by,
        payment_id=payload.payment_id,
    )


@router.post("/{invoice_id}/overdue", response_model=InvoiceRead)
def mark_overdue(
    invoice_id: str,
    as_of_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Mark a past-due open invoice as OVERDUE."""
    return invoice_service.mark_invoice_overdue(db, invoice_id=invoice_id, as_of_date=as_of_date)


@router.post("/{invoice_id}/cancel", response_model=InvoiceRead)
def cancel_existing_invoice(
    invoice_id: str,
    cancel_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Cancel a DRAFT or unpaid SENT/OVERDUE invoice (reversing its ledger posting if already sent)."""
    return invoice_service.cancel_invoice(db, invoice_id=invoice_id, cancel_date=cancel_date)
