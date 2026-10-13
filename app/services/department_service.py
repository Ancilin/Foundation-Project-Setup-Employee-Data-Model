"""Business logic for departments."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Department, Employee


def list_departments(session: Session, include_inactive: bool = False) -> list[Department]:
    """Retrieve all departments."""
    stmt = select(Department).order_by(Department.department_id)
    if not include_inactive:
        stmt = stmt.where(Department.is_active.is_(True))
    return list(session.scalars(stmt).all())


def get_department(session: Session, department_id: str) -> Department:
    """Retrieve a department by ID or raise NotFoundError."""
    dept = session.get(Department, department_id)
    if not dept:
        raise NotFoundError(f"Department '{department_id}' not found")
    return dept


def get_department_employees(
    session: Session, department_id: str, include_inactive: bool = False
) -> list[Employee]:
    """Retrieve all employees belonging to a department."""
    # Ensure department exists first
    get_department(session, department_id)

    stmt = (
        select(Employee)
        .where(Employee.department_id == department_id)
        .order_by(Employee.last_name, Employee.first_name)
    )
    if not include_inactive:
        stmt = stmt.where(Employee.is_active.is_(True))
    return list(session.scalars(stmt).all())
