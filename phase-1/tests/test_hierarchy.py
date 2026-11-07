"""Manager -> team hierarchy (self-referencing employees.manager_id)."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Employee
from tests.helpers import employee_values, make_department, make_employee, make_role


@pytest.fixture
def team(session):
    """CEO -> VP -> (Dev1, Dev2)."""
    make_department(session)
    make_role(session)
    ceo = make_employee(session, "EMP-0001", manager_id=None)
    vp = make_employee(session, "EMP-0002", manager_id="EMP-0001")
    dev1 = make_employee(session, "EMP-0003", manager_id="EMP-0002")
    dev2 = make_employee(session, "EMP-0004", manager_id="EMP-0002")
    session.commit()
    return ceo, vp, dev1, dev2


def test_manager_and_direct_reports_relationships(team):
    ceo, vp, dev1, dev2 = team
    assert ceo.manager is None
    assert dev1.manager is vp
    assert {e.employee_id for e in vp.direct_reports} == {"EMP-0003", "EMP-0004"}
    assert [e.employee_id for e in ceo.direct_reports] == ["EMP-0002"]


def test_walk_up_to_the_top_of_the_hierarchy(team):
    _, _, dev1, _ = team
    chain, person = [], dev1
    while person.manager is not None:
        person = person.manager
        chain.append(person.employee_id)
    assert chain == ["EMP-0002", "EMP-0001"]


def test_top_of_hierarchy_is_the_only_one_without_manager(session, team):
    top = session.scalars(select(Employee).where(Employee.manager_id.is_(None))).all()
    assert [e.employee_id for e in top] == ["EMP-0001"]


def test_employee_cannot_be_their_own_manager(session, team):
    session.add(Employee(**employee_values("EMP-0005", manager_id="EMP-0005")))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_manager_must_exist(session, team):
    session.add(Employee(**employee_values("EMP-0005", manager_id="EMP-9999")))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_manager_cannot_be_hard_deleted_while_they_have_reports(session, team):
    with pytest.raises(IntegrityError):
        session.execute(Employee.__table__.delete().where(Employee.employee_id == "EMP-0002"))
    session.rollback()


def test_deactivated_manager_keeps_their_team(session, team):
    _, vp, dev1, _ = team
    vp.is_active = False
    session.commit()
    assert dev1.manager.employee_id == "EMP-0002"
    assert len(vp.direct_reports) == 2
