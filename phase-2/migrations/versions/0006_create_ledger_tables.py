"""create chart_of_accounts, journal_entries, and journal_lines (LF-09)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. chart_of_accounts
    op.create_table(
        "chart_of_accounts",
        sa.Column("account_code", sa.Integer(), nullable=False),
        sa.Column("account_name", sa.String(128), nullable=False),
        sa.Column("account_type", sa.String(32), nullable=False),
        sa.Column("normal_balance", sa.String(16), nullable=False),
        sa.Column("parent_code", sa.Integer(), nullable=True),
        sa.Column("is_group", sa.String(4), server_default="N", nullable=False),
        sa.Column("statement", sa.String(32), nullable=False),
        sa.Column("is_active", sa.String(4), server_default="Y", nullable=False),
        sa.PrimaryKeyConstraint("account_code", name=op.f("pk_chart_of_accounts")),
    )

    # 2. journal_entries
    op.create_table(
        "journal_entries",
        sa.Column("entry_id", sa.String(20), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("posting_period", sa.String(16), nullable=False),
        sa.Column("financial_year", sa.String(16), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_id", sa.String(32), nullable=False),
        sa.Column("status", sa.String(20), server_default="POSTED", nullable=False),
        sa.Column("total_debit", sa.Numeric(16, 2), nullable=False),
        sa.Column("total_credit", sa.Numeric(16, 2), nullable=False),
        sa.Column("reversal_of_source_id", sa.String(32), nullable=True),
        sa.Column("created_by", sa.String(32), nullable=True),
        sa.Column("created_at", sa.String(32), nullable=True),
        sa.PrimaryKeyConstraint("entry_id", name=op.f("pk_journal_entries")),
    )
    op.create_index("ix_journal_entries_entry_date", "journal_entries", ["entry_date"], unique=False)
    op.create_index("ix_journal_entries_source", "journal_entries", ["source_type", "source_id"], unique=False)

    # 3. journal_lines
    op.create_table(
        "journal_lines",
        sa.Column("line_id", sa.String(20), nullable=False),
        sa.Column("entry_id", sa.String(20), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("account_code", sa.Integer(), nullable=False),
        sa.Column("debit", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("credit", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("cost_center_department_id", sa.String(10), nullable=True),
        sa.Column("line_description", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ["account_code"],
            ["chart_of_accounts.account_code"],
            name=op.f("fk_journal_lines_account_code_chart_of_accounts"),
        ),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["journal_entries.entry_id"],
            name=op.f("fk_journal_lines_entry_id_journal_entries"),
        ),
        sa.PrimaryKeyConstraint("line_id", name=op.f("pk_journal_lines")),
    )
    op.create_index("ix_journal_lines_entry_id", "journal_lines", ["entry_id"], unique=False)
    op.create_index("ix_journal_lines_account_code", "journal_lines", ["account_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_journal_lines_account_code", table_name="journal_lines")
    op.drop_index("ix_journal_lines_entry_id", table_name="journal_lines")
    op.drop_table("journal_lines")
    op.drop_index("ix_journal_entries_source", table_name="journal_entries")
    op.drop_index("ix_journal_entries_entry_date", table_name="journal_entries")
    op.drop_table("journal_entries")
    op.drop_table("chart_of_accounts")
