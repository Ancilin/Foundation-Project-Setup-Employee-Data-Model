"""create statutory_rates, tax_parameters, tax_slabs, payroll_runs, and payroll_items (LF-07)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # 1. statutory_rates
    op.create_table(
        "statutory_rates",
        sa.Column("parameter", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit", sa.String(64), nullable=False),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("parameter", name=op.f("pk_statutory_rates")),
    )

    # 2. tax_parameters
    op.create_table(
        "tax_parameters",
        sa.Column("parameter", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric(14, 2), nullable=False),
        sa.Column("note", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("parameter", name=op.f("pk_tax_parameters")),
    )

    # 3. tax_slabs
    op.create_table(
        "tax_slabs",
        sa.Column("slab_id", sa.String(16), nullable=False),
        sa.Column("regime", sa.String(16), server_default="NEW", nullable=False),
        sa.Column("financial_year", sa.String(16), nullable=False),
        sa.Column("income_from", sa.Numeric(14, 2), nullable=False),
        sa.Column("income_to", sa.Numeric(14, 2), nullable=True),
        sa.Column("rate_percent", sa.Numeric(6, 2), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("note", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("slab_id", name=op.f("pk_tax_slabs")),
    )

    # 4. payroll_runs
    op.create_table(
        "payroll_runs",
        sa.Column("run_id", sa.String(20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("pay_date", sa.Date(), nullable=True),
        sa.Column("employees_paid", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_gross", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("total_deductions", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("total_net", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("total_employer_contributions", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("total_employer_cost", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("status", sa.String(32), server_default="PAID", nullable=False),
        sa.Column("run_by", sa.String(16), nullable=True),
        sa.Column("approved_by", sa.String(16), nullable=True),
        sa.Column("approved_at", sa.String(32), nullable=True),
        sa.Column("idempotency_key", sa.String(64), nullable=True),
        sa.Column("journal_entry_id", sa.String(32), nullable=True),
        sa.Column("calculation_version", sa.String(32), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("run_id", name=op.f("pk_payroll_runs")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_payroll_runs_idempotency_key")),
    )

    # 5. payroll_items
    op.create_table(
        "payroll_items",
        sa.Column("payroll_item_id", sa.String(32), nullable=False),
        sa.Column("run_id", sa.String(20), nullable=False),
        sa.Column("employee_id", sa.String(10), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("department_id", sa.String(10), nullable=False),
        sa.Column("role_id", sa.String(10), nullable=False),
        sa.Column("calendar_days", sa.Integer(), nullable=False),
        sa.Column("days_employed", sa.Integer(), nullable=False),
        sa.Column("lop_days", sa.Numeric(6, 2), server_default="0", nullable=False),
        sa.Column("payable_days", sa.Numeric(6, 2), nullable=False),
        sa.Column("monthly_fixed_gross", sa.Numeric(12, 2), nullable=False),
        sa.Column("basic", sa.Numeric(12, 2), nullable=False),
        sa.Column("hra", sa.Numeric(12, 2), nullable=False),
        sa.Column("conveyance", sa.Numeric(12, 2), nullable=False),
        sa.Column("medical", sa.Numeric(12, 2), nullable=False),
        sa.Column("special_allowance", sa.Numeric(12, 2), nullable=False),
        sa.Column("earned_fixed_pay", sa.Numeric(12, 2), nullable=False),
        sa.Column("overtime_hours_paid", sa.Numeric(6, 2), server_default="0", nullable=False),
        sa.Column("overtime_pay", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("variable_pay", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("variable_pay_type", sa.String(64), nullable=True),
        sa.Column("gross_pay", sa.Numeric(12, 2), nullable=False),
        sa.Column("pf_employee", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("esi_employee", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("professional_tax", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("tds", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("other_deductions", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("total_deductions", sa.Numeric(12, 2), nullable=False),
        sa.Column("net_pay", sa.Numeric(12, 2), nullable=False),
        sa.Column("pf_employer", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("esi_employer", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("employer_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("calculation_note", sa.String(255), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("payroll_item_id", name=op.f("pk_payroll_items")),
        sa.ForeignKeyConstraint(
            ["run_id"], ["payroll_runs.run_id"],
            name=op.f("fk_payroll_items_run_id_payroll_runs"),
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name=op.f("fk_payroll_items_employee_id_employees"),
        ),
        sa.UniqueConstraint("run_id", "employee_id", name="uq_payroll_items_run_employee"),
    )
    op.create_index("ix_payroll_items_run_id", "payroll_items", ["run_id"])
    op.create_index("ix_payroll_items_employee_id", "payroll_items", ["employee_id"])


def downgrade() -> None:
    op.drop_table("payroll_items")
    op.drop_table("payroll_runs")
    op.drop_table("tax_slabs")
    op.drop_table("tax_parameters")
    op.drop_table("statutory_rates")
