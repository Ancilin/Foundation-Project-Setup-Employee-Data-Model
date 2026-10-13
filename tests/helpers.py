"""Small builders so each test only states what it cares about."""

from datetime import date

from app.models import Department, Employee, Role


def make_department(session, department_id="D01", name="Engineering", cost_center="CC-100"):
    dept = Department(department_id=department_id, department_name=name, cost_center=cost_center)
    session.add(dept)
    session.flush()
    return dept


def make_role(session, department_id="D01", role_id="R001", title="Software Engineer", **overrides):
    values = dict(
        role_id=role_id,
        department_id=department_id,
        role_title=title,
        level=2,
        grade="L2 Executive",
        band_min_annual=720000,
        band_mid_annual=900000,
        band_max_annual=1170000,
    )
    values.update(overrides)
    role = Role(**values)
    session.add(role)
    session.flush()
    return role


def employee_values(employee_id="EMP-0001", **overrides):
    """Valid column values for an Employee (assumes D01 / R001 exist)."""
    values = dict(
        employee_id=employee_id,
        first_name="Asha",
        last_name="Rao",
        work_email=f"{employee_id.lower()}@znova-demo.example",
        gender="Female",
        date_of_birth=date(1990, 1, 1),
        hire_date=date(2015, 6, 1),
        work_location="Pune",
        work_mode="Hybrid",
        department_id="D01",
        role_id="R001",
    )
    values.update(overrides)
    return values


def make_employee(session, employee_id="EMP-0001", **overrides):
    emp = Employee(**employee_values(employee_id, **overrides))
    session.add(emp)
    session.flush()
    return emp
