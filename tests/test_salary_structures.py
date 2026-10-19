"""Unit tests for LF-05: Salary structures, revisions, and effective-date boundaries."""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session

from app.models import Department, Employee, Role, SalaryComponent, SalaryRevision, SalaryStructure
from app.services.salary_service import get_structure, revise_salary


@pytest.fixture
def setup_salary_test_data(session: Session):
    """Seed base department, role, component, and employee."""
    dept = Department(
        department_id="D99",
        department_name="Engineering Tech",
        cost_center="CC-99",
        description="Core Tech",
    )
    role = Role(
        role_id="R999",
        department_id="D99",
        role_title="Lead Architect",
        level=5,
        grade="G6",
        band_min_annual=Decimal("1500000.00"),
        band_mid_annual=Decimal("2000000.00"),
        band_max_annual=Decimal("2500000.00"),
        overtime_eligible=False,
    )
    session.add_all([dept, role])
    session.commit()

    # Create components
    comp_basic = SalaryComponent(
        component_id="BASIC",
        component_name="Basic Salary",
        component_type="EARNING",
        taxable="Y",
        calculation_rule="40% of fixed gross",
        is_fixed="Y",
    )
    comp_hra = SalaryComponent(
        component_id="HRA",
        component_name="House Rent Allowance",
        component_type="EARNING",
        taxable="Y",
        calculation_rule="50% of basic",
        is_fixed="Y",
    )
    comp_spl = SalaryComponent(
        component_id="SPECIAL_ALLOWANCE",
        component_name="Special Allowance",
        component_type="EARNING",
        taxable="Y",
        calculation_rule="Balance",
        is_fixed="Y",
    )
    session.add_all([comp_basic, comp_hra, comp_spl])
    session.commit()

    # Create 3 test employees
    employees = []
    for i in range(1, 4):
        emp = Employee(
            employee_id=f"EMP-TEST{i:02d}",
            first_name=f"Tester{i}",
            last_name="Growmar",
            work_email=f"tester{i}@growmar.com",
            gender="Female" if i % 2 == 0 else "Male",
            date_of_birth=date(1992, 5, 10),
            hire_date=date(2023, 1, 1),
            exit_date=None,
            employment_status="Active",
            employment_type="Permanent",
            department_id="D99",
            role_id="R999",
            work_location="Bengaluru",
            work_mode="Hybrid",
        )
        employees.append(emp)
        session.add(emp)

    session.commit()
    return employees


def test_initial_structure_and_get_structure(session: Session, setup_salary_test_data):
    """Test get_structure for an employee active on date."""
    emp = setup_salary_test_data[0]

    # Initial structure starting 2023-01-01
    s1 = SalaryStructure(
        structure_id="SS-T01",
        employee_id=emp.employee_id,
        component_id="BASIC",
        component_name="Basic Salary",
        component_type="EARNING",
        monthly_amount=Decimal("40000.00"),
        effective_from=date(2023, 1, 1),
        effective_to=None,
    )
    s2 = SalaryStructure(
        structure_id="SS-T02",
        employee_id=emp.employee_id,
        component_id="HRA",
        component_name="House Rent Allowance",
        component_type="EARNING",
        monthly_amount=Decimal("20000.00"),
        effective_from=date(2023, 1, 1),
        effective_to=None,
    )
    session.add_all([s1, s2])
    session.commit()

    # Query before start date
    pre_hire = get_structure(session, emp.employee_id, date(2022, 12, 31))
    assert len(pre_hire) == 0

    # Query on start date
    on_hire = get_structure(session, emp.employee_id, date(2023, 1, 1))
    assert len(on_hire) == 2
    assert {s.component_id for s in on_hire} == {"BASIC", "HRA"}
    assert sum(s.monthly_amount for s in on_hire) == Decimal("60000.00")

    # Query in 2024
    in_2024 = get_structure(session, emp.employee_id, date(2024, 6, 15))
    assert len(in_2024) == 2


def test_revise_salary_and_date_boundaries(session: Session, setup_salary_test_data):
    """Test revise_salary correctly closes previous records and checks date boundaries."""
    emp = setup_salary_test_data[1]

    # Initial structure in 2023 (Monthly: 50,000 -> Annual: 600,000)
    session.add(SalaryStructure(
        structure_id="SS-T10",
        employee_id=emp.employee_id,
        component_id="BASIC",
        component_name="Basic Salary",
        component_type="EARNING",
        monthly_amount=Decimal("50000.00"),
        effective_from=date(2023, 1, 1),
        effective_to=None,
    ))
    session.commit()

    # Revision on 2024-04-01: new monthly basic 65,000 (Annual: 780,000 -> +30% increase)
    new_components = [
        {"component_id": "BASIC", "component_name": "Basic Salary", "monthly_amount": "65000.00"}
    ]
    revision, new_structs, is_high_raise = revise_salary(
        session=session,
        employee_id=emp.employee_id,
        new_components=new_components,
        effective_from=date(2024, 4, 1),
        revision_reason="Annual Appraisal",
        role_id_after="R999",
    )

    # Assertions on revision record
    assert revision.previous_annual_fixed == Decimal("600000.00")
    assert revision.new_annual_fixed == Decimal("780000.00")
    assert revision.pct_change == Decimal("30.00")
    assert is_high_raise is True  # > 20% level-up rule triggered

    # Assertions on old structure boundary
    old_struct = session.get(SalaryStructure, "SS-T10")
    assert old_struct.effective_to == date(2024, 3, 31)

    # Verify get_structure boundaries:
    # 1. Day before revision -> returns old salary (50,000)
    struct_before = get_structure(session, emp.employee_id, date(2024, 3, 31))
    assert len(struct_before) == 1
    assert struct_before[0].monthly_amount == Decimal("50000.00")

    # 2. On revision day -> returns new salary (65,000)
    struct_on = get_structure(session, emp.employee_id, date(2024, 4, 1))
    assert len(struct_on) == 1
    assert struct_on[0].monthly_amount == Decimal("65000.00")

    # 3. Later date -> returns new salary (65,000)
    struct_after = get_structure(session, emp.employee_id, date(2025, 1, 1))
    assert len(struct_after) == 1
    assert struct_after[0].monthly_amount == Decimal("65000.00")


def test_three_employees_salary_history(session: Session, setup_salary_test_data):
    """Test salary revisions and history across 3 employees as required by LF-05."""
    for idx, emp in enumerate(setup_salary_test_data):
        # Step 1: Initial salary
        revise_salary(
            session=session,
            employee_id=emp.employee_id,
            new_components=[
                {"component_id": "BASIC", "component_name": "Basic Salary", "monthly_amount": Decimal(40000 + idx * 5000)},
                {"component_id": "HRA", "component_name": "House Rent Allowance", "monthly_amount": Decimal(20000 + idx * 2500)},
            ],
            effective_from=date(2023, 1, 1),
            revision_reason="Joining Compensation",
        )

        # Step 2: Mid-year increment
        revise_salary(
            session=session,
            employee_id=emp.employee_id,
            new_components=[
                {"component_id": "BASIC", "component_name": "Basic Salary", "monthly_amount": Decimal(48000 + idx * 6000)},
                {"component_id": "HRA", "component_name": "House Rent Allowance", "monthly_amount": Decimal(24000 + idx * 3000)},
            ],
            effective_from=date(2024, 1, 1),
            revision_reason="Merit Increment",
        )

        # Query and verify
        components_2023 = get_structure(session, emp.employee_id, date(2023, 6, 1))
        assert len(components_2023) == 2
        assert sum(c.monthly_amount for c in components_2023) == Decimal((40000 + idx * 5000) + (20000 + idx * 2500))

        components_2024 = get_structure(session, emp.employee_id, date(2024, 6, 1))
        assert len(components_2024) == 2
        assert sum(c.monthly_amount for c in components_2024) == Decimal((48000 + idx * 6000) + (24000 + idx * 3000))
