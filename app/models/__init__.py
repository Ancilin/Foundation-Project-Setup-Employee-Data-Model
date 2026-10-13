"""Database models (SQLAlchemy). Importing this package registers every table on Base.metadata,
which Alembic needs in order to see the schema."""

from app.models.base import Base
from app.models.department import Department
from app.models.employee import Employee
from app.models.role import Role

__all__ = ["Base", "Department", "Employee", "Role"]
