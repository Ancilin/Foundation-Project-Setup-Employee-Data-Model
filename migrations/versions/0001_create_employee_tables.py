"""create departments, roles and employees

Revision ID: 0001
Revises:
Create Date: 2026-10-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns() -> list[sa.Column]:
    """is_active (soft delete) + created_at / updated_at, shared by every table."""
    return [
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("department_id", sa.String(10), nullable=False),
        sa.Column("department_name", sa.String(100), nullable=False),
        sa.Column("cost_center", sa.String(20), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("department_id", name=op.f("pk_departments")),
        sa.UniqueConstraint("department_name", name=op.f("uq_departments_department_name")),
        sa.UniqueConstraint("cost_center", name=op.f("uq_departments_cost_center")),
    )

    op.create_table(
        "roles",
        sa.Column("role_id", sa.String(10), nullable=False),
        sa.Column("department_id", sa.String(10), nullable=False),
        sa.Column("role_title", sa.String(100), nullable=False),
        sa.Column("level", sa.SmallInteger(), nullable=False),
        sa.Column("grade", sa.String(60), nullable=False),
        sa.Column("band_min_annual", sa.Numeric(14, 2), nullable=False),
        sa.Column("band_mid_annual", sa.Numeric(14, 2), nullable=False),
        sa.Column("band_max_annual", sa.Numeric(14, 2), nullable=False),
        sa.Column("overtime_eligible", sa.Boolean(), server_default=sa.false(), nullable=False),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("role_id", name=op.f("pk_roles")),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.department_id"],
            name=op.f("fk_roles_department_id_departments"),
        ),
        sa.UniqueConstraint("department_id", "role_title", name=op.f("uq_roles_department_id_role_title")),
        sa.CheckConstraint("level BETWEEN 1 AND 7", name=op.f("ck_roles_level_range")),
        sa.CheckConstraint(
            "band_min_annual <= band_mid_annual AND band_mid_annual <= band_max_annual",
            name=op.f("ck_roles_band_order"),
        ),
    )
    op.create_index("ix_roles_department_id", "roles", ["department_id"])

    op.create_table(
        "employees",
        sa.Column("employee_id", sa.String(10), nullable=False),
        sa.Column("first_name", sa.String(80), nullable=False),
        sa.Column("last_name", sa.String(80), nullable=False),
        sa.Column("work_email", sa.String(255), nullable=False),
        sa.Column("gender", sa.String(10), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column("exit_date", sa.Date(), nullable=True),
        sa.Column("employment_status", sa.String(20), server_default="Active", nullable=False),
        sa.Column("employment_type", sa.String(20), server_default="Permanent", nullable=False),
        sa.Column("work_location", sa.String(80), nullable=False),
        sa.Column("work_mode", sa.String(10), nullable=False),
        sa.Column("department_id", sa.String(10), nullable=False),
        sa.Column("role_id", sa.String(10), nullable=False),
        sa.Column("manager_id", sa.String(10), nullable=True),
        *_audit_columns(),
        sa.PrimaryKeyConstraint("employee_id", name=op.f("pk_employees")),
        sa.UniqueConstraint("work_email", name=op.f("uq_employees_work_email")),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.department_id"],
            name=op.f("fk_employees_department_id_departments"),
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.role_id"], name=op.f("fk_employees_role_id_roles"),
        ),
        sa.ForeignKeyConstraint(
            ["manager_id"], ["employees.employee_id"],
            name=op.f("fk_employees_manager_id_employees"),
        ),
        sa.CheckConstraint("gender IN ('Male', 'Female', 'Other')", name=op.f("ck_employees_gender_valid")),
        sa.CheckConstraint(
            "employment_status IN ('Active', 'Resigned', 'Terminated', 'Contract Ended')",
            name=op.f("ck_employees_employment_status_valid"),
        ),
        sa.CheckConstraint(
            "employment_type IN ('Permanent', 'Fixed-Term Contract')",
            name=op.f("ck_employees_employment_type_valid"),
        ),
        sa.CheckConstraint(
            "work_mode IN ('Onsite', 'Hybrid', 'Remote')", name=op.f("ck_employees_work_mode_valid")
        ),
        sa.CheckConstraint(
            "exit_date IS NULL OR exit_date >= hire_date", name=op.f("ck_employees_exit_after_hire")
        ),
        sa.CheckConstraint("hire_date > date_of_birth", name=op.f("ck_employees_hire_after_birth")),
        sa.CheckConstraint(
            "manager_id IS NULL OR manager_id <> employee_id", name=op.f("ck_employees_not_own_manager")
        ),
    )
    op.create_index("ix_employees_name", "employees", ["last_name", "first_name"])
    op.create_index("ix_employees_department_id", "employees", ["department_id"])
    op.create_index("ix_employees_role_id", "employees", ["role_id"])
    op.create_index("ix_employees_manager_id", "employees", ["manager_id"])
    op.create_index("ix_employees_employment_status", "employees", ["employment_status"])


def downgrade() -> None:
    # Reverse order of creation: employees depends on roles/departments.
    op.drop_table("employees")  # drops its indexes with it
    op.drop_table("roles")
    op.drop_table("departments")
