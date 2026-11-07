"""create assignments, salary components, structures, and revisions (LF-02 and LF-05)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-19
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # 1. employee_assignments table
    op.create_table(
        "employee_assignments",
        sa.Column("assignment_id", sa.String(16), nullable=False),
        sa.Column("employee_id", sa.String(10), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("department_id", sa.String(10), nullable=False),
        sa.Column("role_id", sa.String(10), nullable=False),
        sa.Column("job_level", sa.String(32), nullable=True),
        sa.Column("manager_id", sa.String(10), nullable=True),
        sa.Column("change_reason", sa.String(100), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("assignment_id", name=op.f("pk_employee_assignments")),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name=op.f("fk_assignments_employee_id"),
        ),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.department_id"],
            name=op.f("fk_assignments_department_id"),
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.role_id"],
            name=op.f("fk_assignments_role_id"),
        ),
    )
    op.create_index("ix_assignments_employee_id", "employee_assignments", ["employee_id"])
    op.create_index("ix_assignments_effective_from", "employee_assignments", ["effective_from"])
    op.create_index("ix_assignments_department_id", "employee_assignments", ["department_id"])

    # 2. salary_components table
    op.create_table(
        "salary_components",
        sa.Column("component_id", sa.String(32), nullable=False),
        sa.Column("component_name", sa.String(100), nullable=False),
        sa.Column("component_type", sa.String(32), nullable=False),
        sa.Column("taxable", sa.String(1), server_default="Y", nullable=False),
        sa.Column("calculation_rule", sa.String(255), nullable=True),
        sa.Column("is_fixed", sa.String(1), server_default="Y", nullable=False),
        sa.PrimaryKeyConstraint("component_id", name=op.f("pk_salary_components")),
    )

    # 3. salary_revisions table
    op.create_table(
        "salary_revisions",
        sa.Column("revision_id", sa.String(32), nullable=False),
        sa.Column("employee_id", sa.String(10), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("revision_reason", sa.String(255), nullable=True),
        sa.Column("previous_annual_fixed", sa.Numeric(14, 2), nullable=True),
        sa.Column("new_annual_fixed", sa.Numeric(14, 2), nullable=False),
        sa.Column("pct_change", sa.Numeric(6, 2), nullable=True),
        sa.Column("role_id_after", sa.String(16), nullable=True),
        sa.Column("approved_by", sa.String(10), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("revision_id", name=op.f("pk_salary_revisions")),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name=op.f("fk_revisions_employee_id"),
        ),
    )
    op.create_index("ix_revisions_employee_id", "salary_revisions", ["employee_id"])
    op.create_index("ix_revisions_effective_from", "salary_revisions", ["effective_from"])

    # 4. salary_structures table
    op.create_table(
        "salary_structures",
        sa.Column("structure_id", sa.String(32), nullable=False),
        sa.Column("employee_id", sa.String(10), nullable=False),
        sa.Column("component_id", sa.String(32), nullable=False),
        sa.Column("component_name", sa.String(100), nullable=False),
        sa.Column("component_type", sa.String(32), nullable=False),
        sa.Column("monthly_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("revision_id", sa.String(32), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("structure_id", name=op.f("pk_salary_structures")),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.employee_id"],
            name=op.f("fk_structures_employee_id"),
        ),
        sa.ForeignKeyConstraint(
            ["component_id"], ["salary_components.component_id"],
            name=op.f("fk_structures_component_id"),
        ),
    )
    op.create_index("ix_structures_employee_id", "salary_structures", ["employee_id"])
    op.create_index("ix_structures_effective_from", "salary_structures", ["effective_from"])
    op.create_index("ix_structures_effective_to", "salary_structures", ["effective_to"])


def downgrade() -> None:
    op.drop_table("salary_structures")
    op.drop_table("salary_revisions")
    op.drop_table("salary_components")
    op.drop_table("employee_assignments")
