"""Client, Invoice, InvoiceItem, and InvoicePayment models (LF-10)."""

from datetime import date
from decimal import Decimal
from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Client(Base):
    __tablename__ = "clients"

    client_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    client_name: Mapped[str] = mapped_column(String(128))
    industry: Mapped[str] = mapped_column(String(64))
    city: Mapped[str] = mapped_column(String(64))
    state_or_region: Mapped[str] = mapped_column(String(64))
    country: Mapped[str] = mapped_column(String(8))
    client_type: Mapped[str] = mapped_column(String(16))
    gst_registration: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, server_default="30")
    payment_behaviour: Mapped[str | None] = mapped_column(String(32), nullable=True)
    primary_service_line: Mapped[int] = mapped_column(Integer)
    contact_email: Mapped[str] = mapped_column(String(128))
    onboarded_on: Mapped[date] = mapped_column(Date)
    is_active: Mapped[str] = mapped_column(String(4), default="Y", server_default="Y")

    def __repr__(self) -> str:
        return f"<Client {self.client_id} {self.client_name} ({self.client_type})>"


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_client_id", "client_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_invoice_date", "invoice_date"),
    )

    invoice_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(32), unique=True)
    client_id: Mapped[str] = mapped_column(String(16), ForeignKey("clients.client_id"))
    invoice_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    service_line_account: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(8), default="INR", server_default="INR")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    gst_rate_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("18.00"), server_default="18")
    gst_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0.00"), server_default="0")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0.00"), server_default="0")
    balance_due: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    status: Mapped[str] = mapped_column(String(24), default="DRAFT", server_default="DRAFT")
    last_payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    po_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    carried_in_from_prior_period: Mapped[str] = mapped_column(String(4), default="N", server_default="N")
    created_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ledger_entry_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_id} client={self.client_id} status={self.status} due={self.balance_due}>"


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    __table_args__ = (Index("ix_invoice_items_invoice_id", "invoice_id"),)

    invoice_item_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(String(20), ForeignKey("invoices.invoice_id"))
    line_no: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    revenue_account: Mapped[int] = mapped_column(Integer)

    def __repr__(self) -> str:
        return f"<InvoiceItem {self.invoice_item_id} inv={self.invoice_id} amt={self.amount}>"


class InvoicePayment(Base):
    __tablename__ = "invoice_payments"
    __table_args__ = (Index("ix_invoice_payments_invoice_id", "invoice_id"),)

    payment_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(String(20), ForeignKey("invoices.invoice_id"))
    payment_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    payment_mode: Mapped[str] = mapped_column(String(32))
    reference_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    received_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ledger_entry_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    def __repr__(self) -> str:
        return f"<InvoicePayment {self.payment_id} inv={self.invoice_id} amt={self.amount}>"
