"""Role: a job title within a department, with its grade and salary band."""

from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.employee import Employee


class Role(TimestampMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("department_id", "role_title"),
        CheckConstraint("level BETWEEN 1 AND 7", name="level_range"),
        CheckConstraint(
            "band_min_annual <= band_mid_annual AND band_mid_annual <= band_max_annual",
            name="band_order",
        ),
        Index("ix_roles_department_id", "department_id"),
    )

    role_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.department_id"))
    role_title: Mapped[str] = mapped_column(String(100))
    level: Mapped[int] = mapped_column(SmallInteger)
    grade: Mapped[str] = mapped_column(String(60))
    band_min_annual: Mapped[float] = mapped_column(Numeric(14, 2))
    band_mid_annual: Mapped[float] = mapped_column(Numeric(14, 2))
    band_max_annual: Mapped[float] = mapped_column(Numeric(14, 2))
    overtime_eligible: Mapped[bool] = mapped_column(default=False, server_default=false())

    department: Mapped["Department"] = relationship(back_populates="roles")
    employees: Mapped[list["Employee"]] = relationship(back_populates="role")

    def __repr__(self) -> str:
        return f"<Role {self.role_id} {self.role_title!r}>"
