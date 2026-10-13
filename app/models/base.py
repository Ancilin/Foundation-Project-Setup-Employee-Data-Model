"""Shared model plumbing: naming convention and the timestamp mixin."""

from datetime import datetime

from sqlalchemy import DateTime, MetaData, func, true
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Explicit constraint names make migrations deterministic and rollbacks reliable
# (an unnamed constraint gets a database-generated name that Alembic cannot target).
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base that all ORM models inherit from."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """created_at / updated_at / is_active (soft delete) shared by every table.

    Soft delete: rows are marked `is_active = false` instead of being erased, so
    payroll, leave and reports can still reference them.
    """

    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
