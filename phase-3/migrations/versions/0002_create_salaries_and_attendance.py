"""create salaries and attendance tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # 1. Salaries table
    op.create_table(
        "salaries",
        sa.Column("salary_id", sa.String(32), nullable=False),
        sa.Column("employee_id", sa.String(10), nullable=False),
        sa.Column("monthly_gross", sa.Numeric(12, 2), nullable=False),
        sa.Column("basic", sa.Numeric(12, 2), nullable=False),
        sa.Column("hra", sa.Numeric(12, 2), nullable=False),
        sa.Column("special_allowance", sa.Numeric(12, 2), nullable=False),
        sa.Column("annual_ctc", sa.Numeric(14, 2), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("salary_id", name=op.f("pk_salaries")),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name=op.f("fk_salaries_employee_id_employees"),
        ),
    )
    op.create_index("ix_salaries_employee_id", "salaries", ["employee_id"])
    op.create_index("ix_salaries_effective_from", "salaries", ["effective_from"])

    # 2. Attendance table
    op.create_table(
        "attendance",
        sa.Column("attendance_id", sa.String(32), nullable=False),
        sa.Column("employee_id", sa.String(10), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("weekday", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("check_in", sa.String(10), nullable=True),
        sa.Column("check_out", sa.String(10), nullable=True),
        sa.Column("hours_worked", sa.Numeric(4, 2), server_default="0", nullable=False),
        sa.Column("overtime_hours", sa.Numeric(4, 2), server_default="0", nullable=False),
        sa.Column("late_flag", sa.String(1), server_default="N", nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("attendance_id", name=op.f("pk_attendance")),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name=op.f("fk_attendance_employee_id_employees"),
        ),
        sa.UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_employee_date"),
        sa.CheckConstraint(
            "status IN ('PRESENT', 'ABSENT', 'WFH', 'HALF_DAY', 'ON_LEAVE')",
            name=op.f("ck_attendance_attendance_status_valid"),
        ),
    )
    op.create_index("ix_attendance_employee_date", "attendance", ["employee_id", "attendance_date"])
    op.create_index("ix_attendance_date", "attendance", ["attendance_date"])


def downgrade() -> None:
    op.drop_table("attendance")
    op.drop_table("salaries")
