"""Unit and integration tests for LF-07: Payroll Calculation Engine.

Covers:
1. Rule-by-rule unit tests from real payroll_items rows (LOP, OT, PF, ESI, PT, TDS)
2. 5 hand-checked full rows from payroll_items.csv
3. Decimal vs float (0.1 + 0.2 and ROUND_HALF_UP vs round-half-to-even)
4. POST /payroll/calculate API endpoint
"""

from datetime import date
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Attendance,
    Department,
    Employee,
    Role,
    SalaryComponent,
    SalaryStructure,
    TaxSlab,
)
from app.services.payroll_service import (
    calculate_employee_month,
    calculate_esi,
    calculate_monthly_tds,
    calculate_overtime_pay,
    calculate_pf,
    calculate_professional_tax,
    calculate_prorated_components,
    round_money,
)


def test_rule_1_loss_of_pay_and_component_proration():
    """Rule 1 test from real row PI-000012 (EMP-0029, PR-2025-04):
    30 calendar days, 1.0 LOP day -> 29.0 payable days.
    Full monthly structure: BASIC=26966, HRA=13483, CONV=1600, MED=1250, SPECIAL=24115 (Total=67414).
    """
    components = {
        "BASIC": Decimal("26966"),
        "HRA": Decimal("13483"),
        "CONV": Decimal("1600"),
        "MED": Decimal("1250"),
        "SPECIAL": Decimal("24115"),
    }
    res = calculate_prorated_components(
        components=components,
        calendar_days=30,
        days_employed=30,
        lop_days=Decimal("1.0"),
    )
    assert res["payable_days"] == Decimal("29.00")
    assert res["monthly_fixed_gross"] == Decimal("67414.00")
    assert res["basic"] == Decimal("26067.13")
    assert res["hra"] == Decimal("13033.57")
    assert res["conveyance"] == Decimal("1546.67")
    assert res["medical"] == Decimal("1208.33")
    assert res["special_allowance"] == Decimal("23311.17")
    assert res["earned_fixed_pay"] == Decimal("65166.87")


def test_rule_2_overtime_calculation_cap_and_eligibility():
    """Rule 2 test from real row PI-000004 (EMP-0011, PR-2025-04):
    monthly_fixed_gross = 24041, overtime_hours = 1.5, eligible = True -> 346.75.
    Also verifies 50-hour monthly cap and non-eligible role returning 0.00.
    """
    hrs_paid, ot_pay = calculate_overtime_pay(
        monthly_fixed_gross=Decimal("24041"),
        raw_overtime_hours=Decimal("1.5"),
        overtime_eligible=True,
    )
    assert hrs_paid == Decimal("1.50")
    assert ot_pay == Decimal("346.75")

    # Non-eligible role gets 0 overtime even if hours > 0
    hrs_ineligible, pay_ineligible = calculate_overtime_pay(
        monthly_fixed_gross=Decimal("144460"),
        raw_overtime_hours=Decimal("10.0"),
        overtime_eligible=False,
    )
    assert hrs_ineligible == Decimal("0.00")
    assert pay_ineligible == Decimal("0.00")

    # Overtime hours above 50 are capped at 50.00
    hrs_capped, pay_capped = calculate_overtime_pay(
        monthly_fixed_gross=Decimal("20800"),
        raw_overtime_hours=Decimal("65.0"),
        overtime_eligible=True,
    )
    assert hrs_capped == Decimal("50.00")
    assert pay_capped == Decimal("10000.00")


def test_rule_3_provident_fund_ceiling_and_contract_staff():
    """Rule 3 test from real rows PI-000001 (EMP-0002, basic 57784 -> capped at 15000 -> PF 1800)
    and PI-000009 (EMP-0019, basic 13073 -> 12% = 1568.76).
    """
    # Above 15,000 ceiling -> capped at 1,800.00
    pf_ee_cap, pf_er_cap = calculate_pf(earned_basic=Decimal("57784.00"), pf_applicable=True)
    assert pf_ee_cap == Decimal("1800.00")
    assert pf_er_cap == Decimal("1800.00")

    # Below 15,000 ceiling (PI-000009 EMP-0019: basic 13073.00)
    pf_ee_sub, pf_er_sub = calculate_pf(earned_basic=Decimal("13073.00"), pf_applicable=True)
    assert pf_ee_sub == Decimal("1568.76")
    assert pf_er_sub == Decimal("1568.76")

    # Fixed-term contract staff (pf_applicable=False) -> 0.00
    pf_ee_contract, pf_er_contract = calculate_pf(earned_basic=Decimal("13073.00"), pf_applicable=False)
    assert pf_ee_contract == Decimal("0.00")
    assert pf_er_contract == Decimal("0.00")


def test_rule_4_esi_eligibility_and_rates():
    """Rule 4 test from real row PI-000068 (EMP-0131, PR-2025-04):
    monthly_fixed_gross = 19383 (<= 21,000), gross_pay = 31527.20 ->
    esi_employee (0.75%) = 236.45, esi_employer (3.25%) = 1024.63.
    """
    esi_ee, esi_er = calculate_esi(
        gross_pay=Decimal("31527.20"),
        monthly_fixed_gross=Decimal("19383"),
        pf_or_esi_applicable=True,
    )
    assert esi_ee == Decimal("236.45")
    assert esi_er == Decimal("1024.63")

    # Above 21,000 monthly fixed gross -> 0.00
    esi_ee_high, esi_er_high = calculate_esi(
        gross_pay=Decimal("24041.00"),
        monthly_fixed_gross=Decimal("24041"),
        pf_or_esi_applicable=True,
    )
    assert esi_ee_high == Decimal("0.00")
    assert esi_er_high == Decimal("0.00")


def test_rule_5_professional_tax_threshold():
    """Rule 5 test from real rows PI-000068 (gross 31527.20 >= 25000 -> PT 200)
    and PI-000151 (EMP-0294, gross 19949.10 < 25000 -> PT 0).
    """
    assert calculate_professional_tax(Decimal("31527.20")) == Decimal("200.00")
    assert calculate_professional_tax(Decimal("25000.00")) == Decimal("200.00")
    assert calculate_professional_tax(Decimal("19949.10")) == Decimal("0.00")


def test_rule_6_tds_slabs_rebate_and_marginal_bonus():
    """Rule 6 test from real rows:
    - PI-000001 (EMP-0002): mfg=144460, payable=30/30, vp=34670.40 -> TDS = 18625.79
    - PI-000003 (EMP-0006): mfg=479009, payable=30/30, vp=0 -> TDS = 111100.81
    - PI-000025 (EMP-0049): mfg=465375, payable=29/30 (1 LOP), vp=362992.50 -> TDS = 216539.09
    - Rebate below 12,00,000 taxable (PI-000005 EMP-0012: mfg=53915) -> TDS = 0.00
    """
    tds_emp0002 = calculate_monthly_tds(
        monthly_fixed_gross=Decimal("144460"),
        payable_days=Decimal("30"),
        calendar_days=30,
        variable_pay=Decimal("34670.40"),
    )
    assert tds_emp0002 == Decimal("18625.79")

    tds_emp0006 = calculate_monthly_tds(
        monthly_fixed_gross=Decimal("479009"),
        payable_days=Decimal("30"),
        calendar_days=30,
    )
    assert tds_emp0006 == Decimal("111100.81")

    tds_emp0049 = calculate_monthly_tds(
        monthly_fixed_gross=Decimal("465375"),
        payable_days=Decimal("29.0"),
        calendar_days=30,
        variable_pay=Decimal("362992.50"),
    )
    assert tds_emp0049 == Decimal("216539.09")

    tds_exempt = calculate_monthly_tds(
        monthly_fixed_gross=Decimal("53915"),
        payable_days=Decimal("30"),
        calendar_days=30,
    )
    assert tds_exempt == Decimal("0.00")


def test_five_hand_checked_payroll_items_rows_end_to_end():
    """Unit-test 5 complete hand-checked rows from payroll_items.csv (LF-07 requirement)."""
    # Row 1: PI-000001 (EMP-0002, PR-2025-04) - Full month + Performance Bonus + High-bracket TDS
    r1 = calculate_employee_month(
        employee_id="EMP-0002",
        period_start=date(2025, 4, 1),
        period_end=date(2025, 4, 30),
        components={"BASIC": 57784, "HRA": 28892, "CONV": 1600, "MED": 1250, "SPECIAL": 54934},
        hire_date=date(2020, 7, 13),
        lop_days=Decimal("0.0"),
        raw_overtime_hours=Decimal("0.0"),
        overtime_eligible=False,
        pf_applicable=True,
        variable_pay=Decimal("34670.40"),
        variable_pay_type="Performance Bonus",
        department_id="D08",
        role_id="R047",
    )
    assert r1["earned_fixed_pay"] == Decimal("144460.00")
    assert r1["gross_pay"] == Decimal("179130.40")
    assert r1["pf_employee"] == Decimal("1800.00")
    assert r1["esi_employee"] == Decimal("0.00")
    assert r1["professional_tax"] == Decimal("200.00")
    assert r1["tds"] == Decimal("18625.79")
    assert r1["total_deductions"] == Decimal("20625.79")
    assert r1["net_pay"] == Decimal("158504.61")
    assert r1["employer_cost"] == Decimal("180930.40")

    # Row 2: PI-000004 (EMP-0011, PR-2025-04) - Half-day LOP (0.5) + Overtime (1.5h) + Performance Bonus + Uncapped PF
    r2 = calculate_employee_month(
        employee_id="EMP-0011",
        period_start=date(2025, 4, 1),
        period_end=date(2025, 4, 30),
        components={"BASIC": 9616, "HRA": 4808, "CONV": 1600, "MED": 1250, "SPECIAL": 6767},
        hire_date=date(2020, 11, 2),
        lop_days=Decimal("0.5"),
        raw_overtime_hours=Decimal("1.5"),
        overtime_eligible=True,
        pf_applicable=True,
        variable_pay=Decimal("12982.14"),
        variable_pay_type="Performance Bonus",
        department_id="D07",
        role_id="R039",
    )
    assert r2["earned_fixed_pay"] == Decimal("23640.32")
    assert r2["overtime_pay"] == Decimal("346.75")
    assert r2["gross_pay"] == Decimal("36969.21")
    assert r2["pf_employee"] == Decimal("1134.69")
    assert r2["professional_tax"] == Decimal("200.00")
    assert r2["tds"] == Decimal("0.00")
    assert r2["total_deductions"] == Decimal("1334.69")
    assert r2["net_pay"] == Decimal("35634.52")
    assert r2["employer_cost"] == Decimal("38103.90")

    # Row 3: PI-000012 (EMP-0029, PR-2025-04) - 1.0 LOP day + Performance Bonus
    r3 = calculate_employee_month(
        employee_id="EMP-0029",
        period_start=date(2025, 4, 1),
        period_end=date(2025, 4, 30),
        components={"BASIC": 26966, "HRA": 13483, "CONV": 1600, "MED": 1250, "SPECIAL": 24115},
        hire_date=date(2021, 5, 10),
        lop_days=Decimal("1.0"),
        raw_overtime_hours=Decimal("0.0"),
        overtime_eligible=False,
        pf_applicable=True,
        variable_pay=Decimal("52582.92"),
        variable_pay_type="Performance Bonus",
        department_id="D04",
        role_id="R024",
    )
    assert r3["earned_fixed_pay"] == Decimal("65166.87")
    assert r3["gross_pay"] == Decimal("117749.79")
    assert r3["total_deductions"] == Decimal("2000.00")
    assert r3["net_pay"] == Decimal("115749.79")
    assert r3["employer_cost"] == Decimal("119549.79")

    # Row 4: PI-000025 (EMP-0049, PR-2025-04) - 1.0 LOP day + Executive Bonus + Top-bracket TDS
    r4 = calculate_employee_month(
        employee_id="EMP-0049",
        period_start=date(2025, 4, 1),
        period_end=date(2025, 4, 30),
        components={"BASIC": 186150, "HRA": 93075, "CONV": 1600, "MED": 1250, "SPECIAL": 183300},
        hire_date=date(2020, 3, 16),
        lop_days=Decimal("1.0"),
        raw_overtime_hours=Decimal("0.0"),
        overtime_eligible=False,
        pf_applicable=True,
        variable_pay=Decimal("362992.50"),
        variable_pay_type="Performance Bonus",
        department_id="D10",
        role_id="R058",
    )
    assert r4["earned_fixed_pay"] == Decimal("449862.50")
    assert r4["gross_pay"] == Decimal("812855.00")
    assert r4["tds"] == Decimal("216539.09")
    assert r4["total_deductions"] == Decimal("218539.09")
    assert r4["net_pay"] == Decimal("594315.91")
    assert r4["employer_cost"] == Decimal("814655.00")

    # Row 5: PI-000068 (EMP-0131, PR-2025-04) - ESI applicable (mfg=19383 <= 21000) + Overtime (9h) + Bonus
    r5 = calculate_employee_month(
        employee_id="EMP-0131",
        period_start=date(2025, 4, 1),
        period_end=date(2025, 4, 30),
        components={"BASIC": 7753, "HRA": 3876, "CONV": 800, "MED": 0, "SPECIAL": 6954},
        hire_date=date(2021, 9, 1),
        lop_days=Decimal("0.0"),
        raw_overtime_hours=Decimal("9.0"),
        overtime_eligible=True,
        pf_applicable=True,
        variable_pay=Decimal("10466.82"),
        variable_pay_type="Performance Bonus",
        department_id="D07",
        role_id="R038",
    )
    assert r5["earned_fixed_pay"] == Decimal("19383.00")
    assert r5["overtime_pay"] == Decimal("1677.38")
    assert r5["gross_pay"] == Decimal("31527.20")
    assert r5["pf_employee"] == Decimal("930.36")
    assert r5["esi_employee"] == Decimal("236.45")
    assert r5["esi_employer"] == Decimal("1024.63")
    assert r5["professional_tax"] == Decimal("200.00")
    assert r5["total_deductions"] == Decimal("1366.81")
    assert r5["net_pay"] == Decimal("30160.39")
    assert r5["employer_cost"] == Decimal("33482.19")


def test_why_float_0_1_plus_0_2_fails_and_decimal_fixes_it():
    """Think for yourself: demonstrate why IEEE-754 binary float fails on 0.1 + 0.2 and halfway rounding,
    and how Decimal with ROUND_HALF_UP guarantees exact paisa arithmetic.
    """
    # 1. Binary floating-point representation error on 0.1 + 0.2
    assert (0.1 + 0.2) != 0.3
    assert f"{0.1 + 0.2:.17f}" == "0.30000000000000004"

    # Decimal base-10 representation is exact
    assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")

    # 2. Halfway rounding difference (2.675 rounds down to 2.67 in float, up to 2.68 in Decimal ROUND_HALF_UP)
    assert round(2.675, 2) == 2.67
    assert round_money(Decimal("2.675")) == Decimal("2.68")


def test_payroll_calculate_api_endpoint(session: Session, client: TestClient):
    """Test POST /payroll/calculate computes the exact payslip from DB records."""
    dept = Department(department_id="D08", department_name="Operations", cost_center="CC-008")
    role = Role(
        role_id="R047",
        department_id="D08",
        role_title="Operations Lead",
        level=4,
        grade="L4",
        band_min_annual=1200000,
        band_mid_annual=1600000,
        band_max_annual=2000000,
        overtime_eligible=False,
    )
    emp = Employee(
        employee_id="EMP-0002",
        first_name="Aarav",
        last_name="Sharma",
        work_email="aarav.sharma@znova-demo.example",
        gender="Male",
        date_of_birth=date(1988, 4, 12),
        hire_date=date(2020, 7, 13),
        employment_status="Active",
        employment_type="Permanent",
        department_id="D08",
        role_id="R047",
        work_location="Bengaluru",
        work_mode="Hybrid",
    )
    session.add_all([dept, role, emp])
    session.commit()

    comps = [
        ("BASIC", "Basic Salary", Decimal("57784")),
        ("HRA", "House Rent Allowance", Decimal("28892")),
        ("CONV", "Conveyance Allowance", Decimal("1600")),
        ("MED", "Medical Allowance", Decimal("1250")),
        ("SPECIAL", "Special Allowance", Decimal("54934")),
    ]
    for idx, (cid, cname, amt) in enumerate(comps, start=1):
        session.add(SalaryComponent(component_id=cid, component_name=cname, component_type="EARNING"))
        session.add(
            SalaryStructure(
                structure_id=f"SS-000{idx}",
                employee_id="EMP-0002",
                component_id=cid,
                component_name=cname,
                component_type="EARNING",
                monthly_amount=amt,
                effective_from=date(2025, 4, 1),
                effective_to=None,
            )
        )
    session.add(
        Attendance(
            attendance_id="ATT-1",
            employee_id="EMP-0002",
            attendance_date=date(2025, 4, 1),
            weekday="Tue",
            status="PRESENT",
            check_in="09:00",
            check_out="18:00",
            hours_worked=Decimal("8.00"),
            overtime_hours=Decimal("0.00"),
            late_flag="N",
        )
    )
    session.commit()

    resp = client.post(
        "/payroll/calculate",
        json={
            "employee_id": "EMP-0002",
            "month": "2025-04",
            "variable_pay": "34670.40",
            "variable_pay_type": "Performance Bonus",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(str(body["gross_pay"])) == Decimal("179130.40")
    assert Decimal(str(body["total_deductions"])) == Decimal("20625.79")
    assert Decimal(str(body["net_pay"])) == Decimal("158504.61")
