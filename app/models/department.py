"""Department: an organisational unit that owns roles and employees."""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.role import Role


class Department(TimestampMixin, Base):
    __tablename__ = "departments"

    # Natural key from the dataset (D00 ... D10): the same code is used in every table.
    department_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    department_name: Mapped[str] = mapped_column(String(100), unique=True)
    cost_center: Mapped[str] = mapped_column(String(20), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))

    roles: Mapped[list["Role"]] = relationship(back_populates="department")
    employees: Mapped[list["Employee"]] = relationship(back_populates="department")

    def __repr__(self) -> str:
        return f"<Department {self.department_id} {self.department_name!r}>"
