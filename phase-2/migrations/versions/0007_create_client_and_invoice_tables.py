"""create clients, invoices, invoice_items, and invoice_payments (LF-10)

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. clients
    op.create_table(
        "clients",
        sa.Column("client_id", sa.String(16), nullable=False),
        sa.Column("client_name", sa.String(128), nullable=False),
        sa.Column("industry", sa.String(64), nullable=False),
        sa.Column("city", sa.String(64), nullable=False),
        sa.Column("state_or_region", sa.String(64), nullable=False),
        sa.Column("country", sa.String(8), nullable=False),
        sa.Column("client_type", sa.String(16), nullable=False),
        sa.Column("gst_registration", sa.String(32), nullable=True),
        sa.Column("payment_terms_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("payment_behaviour", sa.String(32), nullable=True),
        sa.Column("primary_service_line", sa.Integer(), nullable=False),
        sa.Column("contact_email", sa.String(128), nullable=False),
        sa.Column("onboarded_on", sa.Date(), nullable=False),
        sa.Column("is_active", sa.String(4), server_default="Y", nullable=False),
        sa.PrimaryKeyConstraint("client_id", name=op.f("pk_clients")),
    )

    # 2. invoices
    op.create_table(
        "invoices",
        sa.Column("invoice_id", sa.String(20), nullable=False),
        sa.Column("invoice_number", sa.String(32), nullable=False),
        sa.Column("client_id", sa.String(16), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("service_line_account", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(8), server_default="INR", nullable=False),
        sa.Column("subtotal", sa.Numeric(16, 2), nullable=False),
        sa.Column("gst_rate_percent", sa.Numeric(6, 2), server_default="18", nullable=False),
        sa.Column("gst_amount", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("total_amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("balance_due", sa.Numeric(16, 2), nullable=False),
        sa.Column("status", sa.String(24), server_default="DRAFT", nullable=False),
        sa.Column("last_payment_date", sa.Date(), nullable=True),
        sa.Column("po_number", sa.String(32), nullable=True),
        sa.Column("carried_in_from_prior_period", sa.String(4), server_default="N", nullable=False),
        sa.Column("created_by", sa.String(32), nullable=True),
        sa.Column("created_at", sa.String(32), nullable=True),
        sa.Column("ledger_entry_id", sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.client_id"], name=op.f("fk_invoices_client_id_clients")),
        sa.PrimaryKeyConstraint("invoice_id", name=op.f("pk_invoices")),
        sa.UniqueConstraint("invoice_number", name=op.f("uq_invoices_invoice_number")),
    )
    op.create_index("ix_invoices_client_id", "invoices", ["client_id"], unique=False)
    op.create_index("ix_invoices_status", "invoices", ["status"], unique=False)
    op.create_index("ix_invoices_invoice_date", "invoices", ["invoice_date"], unique=False)

    # 3. invoice_items
    op.create_table(
        "invoice_items",
        sa.Column("invoice_item_id", sa.String(20), nullable=False),
        sa.Column("invoice_id", sa.String(20), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit_price", sa.Numeric(16, 2), nullable=False),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("revenue_account", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.invoice_id"], name=op.f("fk_invoice_items_invoice_id_invoices")),
        sa.PrimaryKeyConstraint("invoice_item_id", name=op.f("pk_invoice_items")),
    )
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"], unique=False)

    # 4. invoice_payments
    op.create_table(
        "invoice_payments",
        sa.Column("payment_id", sa.String(20), nullable=False),
        sa.Column("invoice_id", sa.String(20), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("payment_mode", sa.String(32), nullable=False),
        sa.Column("reference_no", sa.String(64), nullable=True),
        sa.Column("received_by", sa.String(32), nullable=True),
        sa.Column("ledger_entry_id", sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.invoice_id"], name=op.f("fk_invoice_payments_invoice_id_invoices")),
        sa.PrimaryKeyConstraint("payment_id", name=op.f("pk_invoice_payments")),
    )
    op.create_index("ix_invoice_payments_invoice_id", "invoice_payments", ["invoice_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_invoice_payments_invoice_id", table_name="invoice_payments")
    op.drop_table("invoice_payments")
    op.drop_index("ix_invoice_items_invoice_id", table_name="invoice_items")
    op.drop_table("invoice_items")
    op.drop_index("ix_invoices_invoice_date", table_name="invoices")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_index("ix_invoices_client_id", table_name="invoices")
    op.drop_table("invoices")
    op.drop_table("clients")
