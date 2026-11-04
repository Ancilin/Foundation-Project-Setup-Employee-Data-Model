"""create vendors and expenses tables (LF-11)

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. vendors
    op.create_table(
        "vendors",
        sa.Column("vendor_id", sa.String(16), nullable=False),
        sa.Column("vendor_name", sa.String(128), nullable=False),
        sa.Column("primary_expense_account", sa.Integer(), nullable=False),
        sa.Column("payment_terms_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("city", sa.String(64), nullable=False),
        sa.Column("gst_registration", sa.String(32), nullable=True),
        sa.Column("is_active", sa.String(4), server_default="Y", nullable=False),
        sa.PrimaryKeyConstraint("vendor_id", name=op.f("pk_vendors")),
    )

    # 2. expenses
    op.create_table(
        "expenses",
        sa.Column("expense_id", sa.String(20), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("category_account", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.String(16), nullable=False),
        sa.Column("bill_reference", sa.String(64), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("department_id", sa.String(16), nullable=False),
        sa.Column("amount_excl_gst", sa.Numeric(16, 2), nullable=False),
        sa.Column("gst_rate_percent", sa.Numeric(6, 2), server_default="18", nullable=False),
        sa.Column("gst_amount", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("total_amount", sa.Numeric(16, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(24), server_default="SUBMITTED", nullable=False),
        sa.Column("payment_mode", sa.String(32), nullable=True),
        sa.Column("submitted_by", sa.String(32), nullable=False),
        sa.Column("approved_by", sa.String(32), nullable=True),
        sa.Column("ledger_entry_id", sa.String(20), nullable=True),
        sa.Column("payment_ledger_entry_id", sa.String(20), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["departments.department_id"], name=op.f("fk_expenses_department_id_departments")),
        sa.ForeignKeyConstraint(["vendor_id"], ["vendors.vendor_id"], name=op.f("fk_expenses_vendor_id_vendors")),
        sa.PrimaryKeyConstraint("expense_id", name=op.f("pk_expenses")),
    )
    op.create_index("ix_expenses_vendor_id", "expenses", ["vendor_id"], unique=False)
    op.create_index("ix_expenses_status", "expenses", ["status"], unique=False)
    op.create_index("ix_expenses_expense_date", "expenses", ["expense_date"], unique=False)
    op.create_index("ix_expenses_department_id", "expenses", ["department_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_expenses_department_id", table_name="expenses")
    op.drop_index("ix_expenses_expense_date", table_name="expenses")
    op.drop_index("ix_expenses_status", table_name="expenses")
    op.drop_index("ix_expenses_vendor_id", table_name="expenses")
    op.drop_table("expenses")
    op.drop_table("vendors")
