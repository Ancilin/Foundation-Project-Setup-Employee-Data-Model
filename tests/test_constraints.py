"""Constraint tests: the database itself must reject bad data."""

from datetime import date, datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from tests.helpers import employee_values, make_department, make_employee, make_role
from app.models import Employee


@pytest.fixture
def org(session):
    """One department and one role that employees can point at."""
    dept = make_department(session)
    role = make_role(session)
    session.commit()
    return dept, role


def assert_rejected(session, **employee_overrides):
    session.add(Employee(**employee_values(**employee_overrides)))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


# --- uniqueness / not-null -------------------------------------------------------------------

def test_duplicate_work_email_fails(session, org):
    make_employee(session, "EMP-0001", work_email="same@znova-demo.example")
    session.commit()
    assert_rejected(session, employee_id="EMP-0002", work_email="same@znova-demo.example")


def test_duplicate_employee_id_fails(session, org):
    make_employee(session, "EMP-0001")
    session.commit()
    assert_rejected(session, employee_id="EMP-0001", work_email="other@znova-demo.example")


@pytest.mark.parametrize(
    "field", ["first_name", "last_name", "work_email", "gender", "hire_date", "department_id", "role_id"]
)
def test_required_fields_cannot_be_null(session, org, field):
    assert_rejected(session, **{field: None})


# --- allowed values / date logic -------------------------------------------------------------

@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("gender", "Unknown"),
        ("employment_status", "Fired"),
        ("employment_type", "Intern"),
        ("work_mode", "Moon"),
    ],
)
def test_invalid_enum_values_are_rejected(session, org, field, bad_value):
    assert_rejected(session, **{field: bad_value})


def test_exit_date_before_hire_date_is_rejected(session, org):
    assert_rejected(session, hire_date=date(2020, 1, 1), exit_date=date(2019, 12, 31))


def test_exit_date_on_or_after_hire_date_is_allowed(session, org):
    make_employee(session, hire_date=date(2020, 1, 1), exit_date=date(2020, 1, 1))


def test_hire_date_must_be_after_birth_date(session, org):
    assert_rejected(session, date_of_birth=date(2000, 1, 1), hire_date=date(1999, 1, 1))


# --- foreign keys ----------------------------------------------------------------------------

def test_unknown_department_is_rejected(session, org):
    assert_rejected(session, department_id="D99")


def test_unknown_role_is_rejected(session, org):
    assert_rejected(session, role_id="R999")


def test_role_must_belong_to_existing_department(session, org):
    with pytest.raises(IntegrityError):
        make_role(session, department_id="D99", role_id="R002", title="Ghost")
    session.rollback()


def test_department_with_employees_cannot_be_hard_deleted(session, org):
    make_employee(session)
    session.commit()
    dept, _ = org
    session.delete(session.get(type(dept), "D01"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


# --- departments & roles ---------------------------------------------------------------------

def test_department_name_and_cost_center_are_unique(session, org):
    with pytest.raises(IntegrityError):
        make_department(session, "D02", name="Engineering", cost_center="CC-200")
    session.rollback()
    with pytest.raises(IntegrityError):
        make_department(session, "D02", name="Finance", cost_center="CC-100")
    session.rollback()


def test_role_title_is_unique_within_a_department(session, org):
    with pytest.raises(IntegrityError):
        make_role(session, role_id="R002", title="Software Engineer")
    session.rollback()


def test_same_role_title_allowed_in_another_department(session, org):
    make_department(session, "D02", name="Finance", cost_center="CC-200")
    make_role(session, department_id="D02", role_id="R002", title="Software Engineer")


@pytest.mark.parametrize("level", [0, 8])
def test_role_level_must_be_between_1_and_7(session, org, level):
    with pytest.raises(IntegrityError):
        make_role(session, role_id="R002", title="X", level=level)
    session.rollback()


def test_role_salary_band_must_be_ordered(session, org):
    with pytest.raises(IntegrityError):
        make_role(session, role_id="R002", title="X", band_min_annual=2_000_000)
    session.rollback()


# --- audit columns / soft delete -------------------------------------------------------------

def test_new_employee_is_active_with_timestamps(session, org):
    emp = make_employee(session)
    session.commit()
    assert emp.is_active is True
    assert emp.employment_status == "Active"
    assert emp.created_at is not None and emp.updated_at is not None


def test_soft_delete_keeps_the_row(session, org):
    emp = make_employee(session)
    emp.is_active = False
    session.commit()
    assert session.get(Employee, "EMP-0001") is not None
    assert session.get(Employee, "EMP-0001").is_active is False


def test_updated_at_changes_on_update(session, org):
    old = datetime(2000, 1, 1)
    emp = make_employee(session, updated_at=old)
    session.commit()
    emp.work_location = "Chennai"
    session.commit()
    session.refresh(emp)
    assert emp.updated_at > old


# --- indexes ---------------------------------------------------------------------------------

def test_search_indexes_exist(engine):
    indexes = {ix["name"]: ix["column_names"] for ix in inspect(engine).get_indexes("employees")}
    assert indexes["ix_employees_name"] == ["last_name", "first_name"]
    assert indexes["ix_employees_department_id"] == ["department_id"]
    assert indexes["ix_employees_manager_id"] == ["manager_id"]
    assert indexes["ix_employees_employment_status"] == ["employment_status"]
