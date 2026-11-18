"""add performance indexes for Task 18 query optimization

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-18
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_attendance_date_emp_status",
        "attendance",
        ["attendance_date", "employee_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_journal_entries_status",
        "journal_entries",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_payroll_runs_status",
        "payroll_runs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_payroll_runs_status", table_name="payroll_runs")
    op.drop_index("ix_journal_entries_status", table_name="journal_entries")
    op.drop_index("ix_attendance_date_emp_status", table_name="attendance")
