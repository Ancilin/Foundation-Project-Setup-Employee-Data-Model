"""create holidays, leave_types, leave_balances, leave_requests and enhance attendance (LF-06)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # 1. Enhance attendance table to match official dataset columns & statuses
    op.drop_table("attendance")
    op.create_table(
        "attendance",
        sa.Column("attendance_id", sa.String(32), nullable=False),
        sa.Column("employee_id", sa.String(10), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("weekday", sa.String(10), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("leave_type_code", sa.String(10), nullable=True),
        sa.Column("check_in", sa.String(10), nullable=True),
        sa.Column("check_out", sa.String(10), nullable=True),
        sa.Column("hours_worked", sa.Numeric(4, 2), nullable=True),
        sa.Column("overtime_hours", sa.Numeric(4, 2), server_default="0", nullable=False),
        sa.Column("late_flag", sa.String(1), server_default="N", nullable=False),
        sa.Column("source", sa.String(32), nullable=True),
        sa.Column("data_quality_flag", sa.String(32), nullable=True),
        sa.Column("department_id", sa.String(10), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("attendance_id", name=op.f("pk_attendance")),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name=op.f("fk_attendance_employee_id_employees"),
        ),
        sa.UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_employee_date"),
        sa.CheckConstraint(
            "status IN ('PRESENT', 'ABSENT', 'WFH', 'HALF_DAY', 'ON_LEAVE', 'PAID_LEAVE', 'ABSENT_LOP', 'HALF_DAY_UNPAID', 'UNPAID_LEAVE', 'HALF_DAY_PAID')",
            name=op.f("ck_attendance_attendance_status_valid"),
        ),
    )
    op.create_index("ix_attendance_employee_date", "attendance", ["employee_id", "attendance_date"])
    op.create_index("ix_attendance_date", "attendance", ["attendance_date"])

    # 2. holidays table
    op.create_table(
        "holidays",
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("holiday_name", sa.String(150), nullable=False),
        sa.Column("holiday_type", sa.String(32), nullable=False),
        sa.Column("weekday", sa.String(16), nullable=False),
        sa.Column("falls_on_weekend", sa.String(1), server_default="N", nullable=False),
        sa.Column("calendar_note", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("holiday_date", name=op.f("pk_holidays")),
    )

    # 3. leave_types table
    op.create_table(
        "leave_types",
        sa.Column("leave_type_code", sa.String(10), nullable=False),
        sa.Column("leave_type_name", sa.String(100), nullable=False),
        sa.Column("pay_type", sa.String(20), nullable=False),
        sa.Column("annual_quota_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("prorated_for_joiners", sa.String(1), server_default="N", nullable=False),
        sa.Column("carry_forward_allowed", sa.String(1), server_default="N", nullable=False),
        sa.Column("max_carry_forward_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("policy_note", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("leave_type_code", name=op.f("pk_leave_types")),
    )

    # 4. leave_balances table
    op.create_table(
        "leave_balances",
        sa.Column("employee_id", sa.String(10), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("financial_year", sa.String(16), nullable=False),
        sa.Column("cl_entitlement", sa.Numeric(6, 2), server_default="12", nullable=False),
        sa.Column("cl_used", sa.Numeric(6, 2), server_default="0", nullable=False),
        sa.Column("cl_balance", sa.Numeric(6, 2), server_default="12", nullable=False),
        sa.Column("sl_entitlement", sa.Numeric(6, 2), server_default="12", nullable=False),
        sa.Column("sl_used", sa.Numeric(6, 2), server_default="0", nullable=False),
        sa.Column("sl_balance", sa.Numeric(6, 2), server_default="12", nullable=False),
        sa.Column("el_used_fy", sa.Numeric(6, 2), server_default="0", nullable=False),
        sa.Column("el_balance", sa.Numeric(6, 2), server_default="0", nullable=False),
        sa.Column("pending_days", sa.Numeric(6, 2), server_default="0", nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("employee_id", name=op.f("pk_leave_balances")),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name=op.f("fk_leave_balances_employee_id_employees"),
        ),
    )

    # 5. leave_requests table
    op.create_table(
        "leave_requests",
        sa.Column("leave_request_id", sa.String(32), nullable=False),
        sa.Column("employee_id", sa.String(10), nullable=False),
        sa.Column("leave_type_code", sa.String(10), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("days", sa.Numeric(6, 2), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), server_default="Pending", nullable=False),
        sa.Column("applied_on", sa.Date(), nullable=False),
        sa.Column("approver_id", sa.String(10), nullable=True),
        sa.Column("decided_on", sa.Date(), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("leave_request_id", name=op.f("pk_leave_requests")),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name=op.f("fk_leave_requests_employee_id_employees"),
        ),
        sa.ForeignKeyConstraint(
            ["leave_type_code"], ["leave_types.leave_type_code"],
            name=op.f("fk_leave_requests_leave_type_code_leave_types"),
        ),
        sa.ForeignKeyConstraint(
            ["approver_id"], ["employees.employee_id"],
            name=op.f("fk_leave_requests_approver_id_employees"),
        ),
        sa.CheckConstraint(
            "status IN ('Pending', 'Approved', 'Rejected', 'Cancelled')",
            name=op.f("ck_leave_requests_leave_request_status_valid"),
        ),
    )
    op.create_index("ix_leave_requests_employee_id", "leave_requests", ["employee_id"])
    op.create_index("ix_leave_requests_start_date", "leave_requests", ["start_date"])


def downgrade() -> None:
    op.drop_table("leave_requests")
    op.drop_table("leave_balances")
    op.drop_table("leave_types")
    op.drop_table("holidays")
    op.drop_table("attendance")
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
