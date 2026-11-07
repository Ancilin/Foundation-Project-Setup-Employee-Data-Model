"""API tests for department endpoints."""

from tests.helpers import make_department, make_employee, make_role


def test_list_departments_empty(client):
    res = client.get("/departments")
    assert res.status_code == 200
    assert res.json() == []


def test_list_departments_populated(client, session):
    make_department(session, "D01", "Engineering", "CC-100")
    make_department(session, "D02", "Product", "CC-200")
    session.commit()

    res = client.get("/departments")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    ids = [d["department_id"] for d in data]
    assert ids == ["D01", "D02"]


def test_get_department_employees(client, session):
    make_department(session, "D01", "Engineering", "CC-100")
    make_department(session, "D02", "Sales", "CC-300")
    make_role(session, "D01", "R001", "Software Engineer")
    make_role(session, "D02", "R002", "Sales Executive")

    make_employee(session, "EMP-0001", department_id="D01", role_id="R001", work_email="emp1@test.com")
    make_employee(session, "EMP-0002", department_id="D01", role_id="R001", work_email="emp2@test.com")
    make_employee(session, "EMP-0003", department_id="D02", role_id="R002", work_email="emp3@test.com")
    session.commit()

    res = client.get("/departments/D01/employees")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert {e["employee_id"] for e in data} == {"EMP-0001", "EMP-0002"}


def test_get_department_employees_not_found(client):
    res = client.get("/departments/D99/employees")
    assert res.status_code == 404
    data = res.json()
    assert "detail" in data
    assert data["error_code"] == "NOT_FOUND"
