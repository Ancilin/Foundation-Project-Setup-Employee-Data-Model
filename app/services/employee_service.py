"""Business logic for employees."""

import re
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models import Department, Employee, Role
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


def _next_employee_id(session: Session) -> str:
    """Generate the next sequential employee ID (e.g. EMP-0747)."""
    stmt = select(Employee.employee_id).where(Employee.employee_id.like("EMP-%"))
    ids = session.scalars(stmt).all()
    max_num = 0
    for eid in ids:
        match = re.match(r"^EMP-(\d+)$", eid)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"EMP-{max_num + 1:04d}"


def _check_hierarchy_cycle(session: Session, employee_id: str, new_manager_id: str) -> None:
    """Ensure setting new_manager_id does not create a circular reporting chain."""
    visited = {employee_id}
    curr = new_manager_id
    while curr:
        if curr in visited:
            raise ValidationError(
                f"Setting manager to '{new_manager_id}' creates a circular management hierarchy"
            )
        visited.add(curr)
        manager_record = session.get(Employee, curr)
        if not manager_record:
            break
        curr = manager_record.manager_id


def list_employees(
    session: Session,
    page: int = 1,
    size: int = 20,
    department: str | None = None,
    status: str | None = None,
    q: str | None = None,
    include_inactive: bool = False,
) -> tuple[list[Employee], int]:
    """List employees with pagination, filtering, and text search.

    Returns:
        tuple[list[Employee], int]: (items, total_count)
    """
    stmt = select(Employee)

    if not include_inactive:
        stmt = stmt.where(Employee.is_active.is_(True))

    if department:
        stmt = stmt.where(Employee.department_id == department.strip())

    if status:
        stmt = stmt.where(Employee.employment_status == status.strip())

    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Employee.first_name.ilike(term),
                Employee.last_name.ilike(term),
                (Employee.first_name + " " + Employee.last_name).ilike(term),
                Employee.work_email.ilike(term),
                Employee.employee_id.ilike(term),
            )
        )

    # Count total matching records
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = session.scalar(count_stmt) or 0

    # Paginate and order by ID
    offset = (page - 1) * size
    stmt = stmt.order_by(Employee.employee_id).offset(offset).limit(size)
    items = list(session.scalars(stmt).all())

    return items, total


def get_employee(session: Session, employee_id: str) -> Employee:
    """Get single employee by ID."""
    emp = session.get(Employee, employee_id)
    if not emp:
        raise NotFoundError(f"Employee '{employee_id}' not found")
    return emp


def get_direct_reports(
    session: Session, employee_id: str, include_inactive: bool = False
) -> list[Employee]:
    """Retrieve all direct reports for a manager."""
    # Ensure manager exists
    get_employee(session, employee_id)

    stmt = select(Employee).where(Employee.manager_id == employee_id).order_by(Employee.employee_id)
    if not include_inactive:
        stmt = stmt.where(Employee.is_active.is_(True))
    return list(session.scalars(stmt).all())


def create_employee(session: Session, data: EmployeeCreate) -> Employee:
    """Create a new employee with domain validations."""
    # 1. Determine employee_id
    emp_id = data.employee_id or _next_employee_id(session)
    if session.get(Employee, emp_id):
        raise ConflictError(f"Employee with ID '{emp_id}' already exists")

    # 2. Check work_email uniqueness
    existing_email = session.scalar(
        select(Employee).where(Employee.work_email == str(data.work_email).lower())
    )
    if existing_email:
        raise ConflictError(f"Work email '{data.work_email}' is already registered")

    # 3. Verify department and role foreign keys
    if not session.get(Department, data.department_id):
        raise NotFoundError(f"Department '{data.department_id}' does not exist")

    role = session.get(Role, data.role_id)
    if not role:
        raise NotFoundError(f"Role '{data.role_id}' does not exist")

    # 4. Verify manager
    if data.manager_id:
        if data.manager_id == emp_id:
            raise ValidationError("An employee cannot be their own manager")
        if not session.get(Employee, data.manager_id):
            raise NotFoundError(f"Reporting manager '{data.manager_id}' does not exist")

    # 5. Date logic
    if data.exit_date and data.exit_date < data.hire_date:
        raise ValidationError("Exit date cannot precede hire date")
    if data.hire_date <= data.date_of_birth:
        raise ValidationError("Hire date must be after date of birth")

    emp = Employee(
        employee_id=emp_id,
        first_name=data.first_name,
        last_name=data.last_name,
        work_email=str(data.work_email).lower(),
        gender=data.gender,
        date_of_birth=data.date_of_birth,
        hire_date=data.hire_date,
        exit_date=data.exit_date,
        employment_status=data.employment_status,
        employment_type=data.employment_type,
        work_location=data.work_location,
        work_mode=data.work_mode,
        department_id=data.department_id,
        role_id=data.role_id,
        manager_id=data.manager_id,
    )
    session.add(emp)
    session.commit()
    session.refresh(emp)
    return emp


def update_employee(session: Session, employee_id: str, data: EmployeeUpdate) -> Employee:
    """Partially update an employee with validation."""
    emp = get_employee(session, employee_id)
    payload = data.model_dump(exclude_unset=True)

    if not payload:
        return emp

    # 1. Email check if changing
    if "work_email" in payload and payload["work_email"]:
        new_email = str(payload["work_email"]).lower()
        if new_email != emp.work_email:
            existing = session.scalar(select(Employee).where(Employee.work_email == new_email))
            if existing:
                raise ConflictError(f"Work email '{new_email}' is already taken")
            payload["work_email"] = new_email

    # 2. Check foreign keys
    if "department_id" in payload and payload["department_id"]:
        if not session.get(Department, payload["department_id"]):
            raise NotFoundError(f"Department '{payload['department_id']}' does not exist")

    if "role_id" in payload and payload["role_id"]:
        if not session.get(Role, payload["role_id"]):
            raise NotFoundError(f"Role '{payload['role_id']}' does not exist")

    # 3. Manager check & cycle prevention
    if "manager_id" in payload:
        new_mgr = payload["manager_id"]
        if new_mgr:
            if new_mgr == employee_id:
                raise ValidationError("An employee cannot be their own manager")
            if not session.get(Employee, new_mgr):
                raise NotFoundError(f"Reporting manager '{new_mgr}' does not exist")
            _check_hierarchy_cycle(session, employee_id, new_mgr)

    # 4. Dates check
    new_hire = payload.get("hire_date", emp.hire_date)
    new_dob = payload.get("date_of_birth", emp.date_of_birth)
    new_exit = payload.get("exit_date", emp.exit_date)

    if new_hire <= new_dob:
        raise ValidationError("Hire date must be after date of birth")
    if new_exit and new_exit < new_hire:
        raise ValidationError("Exit date cannot precede hire date")

    for k, v in payload.items():
        setattr(emp, k, v)

    session.commit()
    session.refresh(emp)
    return emp


def delete_employee(session: Session, employee_id: str) -> Employee:
    """Soft delete an employee (sets is_active = False)."""
    emp = get_employee(session, employee_id)
    emp.is_active = False
    session.commit()
    session.refresh(emp)
    return emp
