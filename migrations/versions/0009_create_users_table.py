"""create users table for JWT auth and RBAC (LF-13)

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-02
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(16), nullable=False),
        sa.Column("employee_id", sa.String(16), nullable=False),
        sa.Column("username", sa.String(128), nullable=False),
        sa.Column("role", sa.String(24), server_default="EMPLOYEE", nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.String(4), server_default="Y", nullable=False),
        sa.Column("mfa_enabled", sa.String(4), server_default="N", nullable=False),
        sa.Column("last_login_at", sa.String(32), nullable=True),
        sa.Column("created_at", sa.String(32), nullable=True),
        sa.Column("password_policy_note", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.employee_id"], name=op.f("fk_users_employee_id_employees")),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_users")),
        sa.UniqueConstraint("employee_id", name="uq_users_employee_id"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )
    op.create_index("ix_users_role", "users", ["role"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_role", table_name="users")
    op.drop_table("users")
