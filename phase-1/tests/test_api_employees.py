"""API tests for employee CRUD, team hierarchy, pagination, filters, and search."""

from datetime import date, timedelta
from tests.helpers import make_department, make_employee, make_role


def setup_org(session):
    dept = make_department(session, "D01", "Engineering", "CC-100")
    role = make_role(session, "D01", "R001", "Software Engineer")
    session.commit()
    return dept, role


def valid_employee_payload(**overrides):
    payload = {
        "first_name": "Aarav",
        "last_name": "Patel",
        "work_email": "aarav.patel@znova-demo.example",
        "gender": "Male",
        "date_of_birth": "1992-05-14",
        "hire_date": "2020-03-01",
        "employment_status": "Active",
        "employment_type": "Permanent",
        "work_location": "Pune",
        "work_mode": "Hybrid",
        "department_id": "D01",
        "role_id": "R001",
    }
    payload.update(overrides)
    return payload


# --- Create (POST /employees) ------------------------------------------------

def test_create_employee_success(client, session):
    setup_org(session)
    payload = valid_employee_payload()
    res = client.post("/employees", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["employee_id"] == "EMP-0001"
    assert data["first_name"] == "Aarav"
    assert data["last_name"] == "Patel"
    assert data["full_name"] == "Aarav Patel"
    assert data["work_email"] == "aarav.patel@znova-demo.example"
    assert data["is_active"] is True


def test_create_employee_with_explicit_id(client, session):
    setup_org(session)
    payload = valid_employee_payload(employee_id="EMP-9999", work_email="custom@test.com")
    res = client.post("/employees", json=payload)
    assert res.status_code == 201
    assert res.json()["employee_id"] == "EMP-9999"


def test_create_employee_duplicate_email(client, session):
    setup_org(session)
    client.post("/employees", json=valid_employee_payload(work_email="dup@test.com"))
    res = client.post("/employees", json=valid_employee_payload(work_email="dup@test.com"))
    assert res.status_code == 409
    data = res.json()
    assert data["error_code"] == "CONFLICT"
    assert "already registered" in data["detail"]


def test_create_employee_invalid_email_format(client, session):
    setup_org(session)
    res = client.post("/employees", json=valid_employee_payload(work_email="not-an-email"))
    assert res.status_code == 422
    data = res.json()
    assert data["error_code"] == "VALIDATION_ERROR"


def test_create_employee_future_hire_date(client, session):
    setup_org(session)
    future = (date.today() + timedelta(days=10)).isoformat()
    res = client.post("/employees", json=valid_employee_payload(hire_date=future))
    assert res.status_code == 422
    data = res.json()
    assert data["error_code"] == "VALIDATION_ERROR"
    assert "future" in data["detail"].lower()


def test_create_employee_empty_or_whitespace_name(client, session):
    setup_org(session)
    res = client.post("/employees", json=valid_employee_payload(first_name="   "))
    assert res.status_code == 422
    data = res.json()
    assert data["error_code"] == "VALIDATION_ERROR"


def test_create_employee_nonexistent_department(client, session):
    setup_org(session)
    res = client.post("/employees", json=valid_employee_payload(department_id="D99"))
    assert res.status_code == 404
    assert res.json()["error_code"] == "NOT_FOUND"


def test_create_employee_nonexistent_role(client, session):
    setup_org(session)
    res = client.post("/employees", json=valid_employee_payload(role_id="R999"))
    assert res.status_code == 404
    assert res.json()["error_code"] == "NOT_FOUND"


def test_create_employee_self_manager_rejected(client, session):
    setup_org(session)
    res = client.post("/employees", json=valid_employee_payload(employee_id="EMP-0001", manager_id="EMP-0001"))
    assert res.status_code == 422
    assert res.json()["error_code"] == "VALIDATION_ERROR"


# --- Read (GET /employees/{id}) ----------------------------------------------

def test_get_employee_success(client, session):
    setup_org(session)
    make_employee(session, "EMP-0001", first_name="Priya", last_name="Sharma")
    session.commit()

    res = client.get("/employees/EMP-0001")
    assert res.status_code == 200
    data = res.json()
    assert data["employee_id"] == "EMP-0001"
    assert data["full_name"] == "Priya Sharma"


def test_get_employee_not_found(client):
    res = client.get("/employees/EMP-9999")
    assert res.status_code == 404
    assert res.json()["error_code"] == "NOT_FOUND"


# --- Update (PATCH /employees/{id}) ------------------------------------------

def test_update_employee_partial(client, session):
    setup_org(session)
    make_employee(session, "EMP-0001")
    session.commit()

    res = client.patch(
        "/employees/EMP-0001",
        json={"work_location": "Bengaluru", "work_mode": "Remote"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["work_location"] == "Bengaluru"
    assert data["work_mode"] == "Remote"
    assert data["first_name"] == "Asha"  # Unchanged


def test_update_employee_cycle_prevention(client, session):
    setup_org(session)
    # Emp 1 manages Emp 2
    make_employee(session, "EMP-0001", manager_id=None)
    make_employee(session, "EMP-0002", manager_id="EMP-0001", work_email="e2@test.com")
    session.commit()

    # Attempt to set Emp 1's manager to Emp 2 (circular)
    res = client.patch("/employees/EMP-0001", json={"manager_id": "EMP-0002"})
    assert res.status_code == 422
    data = res.json()
    assert data["error_code"] == "VALIDATION_ERROR"
    assert "circular" in data["detail"].lower()


# --- Delete (DELETE /employees/{id} - soft delete) ---------------------------

def test_soft_delete_employee(client, session):
    setup_org(session)
    make_employee(session, "EMP-0001")
    session.commit()

    res = client.delete("/employees/EMP-0001")
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    # Soft-deleted employee should not appear in default active list
    list_res = client.get("/employees")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 0

    # But appears if include_inactive=true
    all_res = client.get("/employees?include_inactive=true")
    assert all_res.status_code == 200
    assert all_res.json()["total"] == 1


# --- List, Pagination, Filtering & Search ------------------------------------

def test_list_employees_pagination(client, session):
    setup_org(session)
    for i in range(1, 16):
        make_employee(session, f"EMP-{i:04d}", work_email=f"user{i}@test.com")
    session.commit()

    res = client.get("/employees?page=1&size=5")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 15
    assert data["page"] == 1
    assert data["size"] == 5
    assert data["pages"] == 3
    assert len(data["items"]) == 5
    assert data["items"][0]["employee_id"] == "EMP-0001"

    # Page 3
    res3 = client.get("/employees?page=3&size=5")
    assert len(res3.json()["items"]) == 5
    assert res3.json()["items"][0]["employee_id"] == "EMP-0011"


def test_list_employees_filtering_and_search(client, session):
    setup_org(session)
    make_department(session, "D02", "Product", "CC-200")
    make_role(session, "D02", "R002", "Product Manager")

    make_employee(session, "EMP-0001", first_name="Vikram", last_name="Seth", department_id="D01", work_email="vikram@test.com")
    make_employee(session, "EMP-0002", first_name="Ananya", last_name="Pandey", department_id="D01", employment_status="Resigned", work_email="ananya@test.com")
    make_employee(session, "EMP-0003", first_name="Vikram", last_name="Batra", department_id="D02", role_id="R002", work_email="batra@test.com")
    session.commit()

    # Filter by department
    d1 = client.get("/employees?department=D01").json()
    assert d1["total"] == 2

    # Filter by status
    st = client.get("/employees?status=Resigned").json()
    assert st["total"] == 1
    assert st["items"][0]["first_name"] == "Ananya"

    # Search name 'Vikram' across departments
    srch = client.get("/employees?q=Vikram").json()
    assert srch["total"] == 2

    # Combined: search 'Vikram' in department D01
    combined = client.get("/employees?q=Vikram&department=D01").json()
    assert combined["total"] == 1
    assert combined["items"][0]["employee_id"] == "EMP-0001"


# --- Team (GET /employees/{id}/team) -----------------------------------------

def test_get_employee_team(client, session):
    setup_org(session)
    make_employee(session, "EMP-0001", manager_id=None)
    make_employee(session, "EMP-0002", manager_id="EMP-0001", work_email="sub1@test.com")
    make_employee(session, "EMP-0003", manager_id="EMP-0001", work_email="sub2@test.com")
    make_employee(session, "EMP-0004", manager_id="EMP-0002", work_email="sub3@test.com")
    session.commit()

    res = client.get("/employees/EMP-0001/team")
    assert res.status_code == 200
    team = res.json()
    assert len(team) == 2
    assert {e["employee_id"] for e in team} == {"EMP-0002", "EMP-0003"}


def test_get_employee_team_not_found(client):
    res = client.get("/employees/EMP-9999/team")
    assert res.status_code == 404
    assert res.json()["error_code"] == "NOT_FOUND"


# --- Root redirect -----------------------------------------------------------

def test_root_redirect_to_docs(client):
    res = client.get("/", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert res.headers["location"] == "/docs"
