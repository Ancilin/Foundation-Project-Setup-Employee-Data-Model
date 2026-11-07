"""Payroll calculation engine (LF-07): pure functions for gross-to-net pay with Decimal ROUND_HALF_UP."""

import calendar
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.employee import Employee
from app.models.payroll import StatutoryRate, TaxParameter, TaxSlab
from app.models.role import Role
from app.models.salary import SalaryStructure
from app.services.attendance_service import monthly_summary

TWO_PLACES = Decimal("0.01")

DEFAULT_TAX_SLABS = [
    {"income_from": Decimal("0"), "income_to": Decimal("400000"), "rate_percent": Decimal("0")},
    {"income_from": Decimal("400000"), "income_to": Decimal("800000"), "rate_percent": Decimal("5")},
    {"income_from": Decimal("800000"), "income_to": Decimal("1200000"), "rate_percent": Decimal("10")},
    {"income_from": Decimal("1200000"), "income_to": Decimal("1600000"), "rate_percent": Decimal("15")},
    {"income_from": Decimal("1600000"), "income_to": Decimal("2000000"), "rate_percent": Decimal("20")},
    {"income_from": Decimal("2000000"), "income_to": Decimal("2400000"), "rate_percent": Decimal("25")},
    {"income_from": Decimal("2400000"), "income_to": None, "rate_percent": Decimal("30")},
]


def to_dec(val: Decimal | int | float | str | None) -> Decimal:
    if val is None or val == "":
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def round_money(val: Decimal | int | float | str) -> Decimal:
    """Round half-up to 2 decimal places (to the paisa) using Decimal."""
    return to_dec(val).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calculate_days_employed(
    period_start: date,
    period_end: date,
    hire_date: date,
    exit_date: date | None = None,
) -> int:
    """Compute calendar days employed within [period_start, period_end] for joiners and leavers."""
    eff_start = max(period_start, hire_date)
    eff_end = min(period_end, exit_date) if exit_date is not None else period_end
    if eff_end < eff_start:
        return 0
    return (eff_end - eff_start).days + 1


def calculate_prorated_components(
    components: dict[str, Decimal | int | float | str],
    calendar_days: int,
    days_employed: int,
    lop_days: Decimal | int | float | str,
) -> dict[str, Decimal]:
    """Rule 1 (Loss of Pay & Proration):
    Each fixed salary component (BASIC, HRA, CONV, MED, SPECIAL) is prorated on a calendar-day basis:
      payable_days = days_employed - lop_days
      earned_component = round_half_up(component_monthly * payable_days / calendar_days)
      earned_fixed_pay = basic + hra + conveyance + medical + special_allowance
    """
    cal_dec = to_dec(calendar_days)
    lop_dec = round_money(lop_days)
    payable_days = round_money(to_dec(days_employed) - lop_dec)
    if payable_days < Decimal("0.00"):
        payable_days = Decimal("0.00")

    b_full = to_dec(components.get("BASIC", 0))
    h_full = to_dec(components.get("HRA", 0))
    c_full = to_dec(components.get("CONV", 0))
    m_full = to_dec(components.get("MED", 0))
    s_full = to_dec(components.get("SPECIAL", components.get("SPECIAL_ALLOWANCE", 0)))

    monthly_fixed_gross = round_money(b_full + h_full + c_full + m_full + s_full)

    basic = round_money(b_full * payable_days / cal_dec)
    hra = round_money(h_full * payable_days / cal_dec)
    conveyance = round_money(c_full * payable_days / cal_dec)
    medical = round_money(m_full * payable_days / cal_dec)
    special_allowance = round_money(s_full * payable_days / cal_dec)
    earned_fixed_pay = round_money(basic + hra + conveyance + medical + special_allowance)

    return {
        "payable_days": payable_days,
        "monthly_fixed_gross": monthly_fixed_gross,
        "basic": basic,
        "hra": hra,
        "conveyance": conveyance,
        "medical": medical,
        "special_allowance": special_allowance,
        "earned_fixed_pay": earned_fixed_pay,
    }


def calculate_overtime_pay(
    monthly_fixed_gross: Decimal | int | float | str,
    raw_overtime_hours: Decimal | int | float | str,
    overtime_eligible: bool,
    ot_multiplier: Decimal = Decimal("2.0"),
    ot_cap_hours: Decimal = Decimal("50.0"),
    working_hours_per_month: Decimal = Decimal("208.0"),
) -> tuple[Decimal, Decimal]:
    """Rule 2 (Overtime):
    Paid only to overtime-eligible roles:
      overtime_hours_paid = min(raw_overtime_hours, 50.0)
      overtime_pay = round_half_up(overtime_hours_paid * (monthly_fixed_gross / 208) * 2)
    """
    if not overtime_eligible:
        return Decimal("0.00"), Decimal("0.00")

    hrs = to_dec(raw_overtime_hours)
    if hrs <= Decimal("0.00"):
        return Decimal("0.00"), Decimal("0.00")

    hours_paid = round_money(min(hrs, to_dec(ot_cap_hours)))
    mfg = to_dec(monthly_fixed_gross)
    ot_pay = round_money(hours_paid * (mfg / to_dec(working_hours_per_month)) * to_dec(ot_multiplier))
    return hours_paid, ot_pay


def calculate_pf(
    earned_basic: Decimal | int | float | str,
    pf_applicable: bool,
    pf_ee_rate: Decimal = Decimal("12.0"),
    pf_er_rate: Decimal = Decimal("12.0"),
    pf_wage_ceiling: Decimal = Decimal("15000.0"),
) -> tuple[Decimal, Decimal]:
    """Rule 3 (Provident Fund - PF):
    Applies to permanent staff (pf_applicable = True):
      pf_wage = min(earned_basic, 15000)
      pf_employee = round_half_up(pf_wage * 12%)
      pf_employer = round_half_up(pf_wage * 12%)
    """
    if not pf_applicable:
        return Decimal("0.00"), Decimal("0.00")

    pf_base = min(to_dec(earned_basic), to_dec(pf_wage_ceiling))
    pf_ee = round_money(pf_base * to_dec(pf_ee_rate) / Decimal("100"))
    pf_er = round_money(pf_base * to_dec(pf_er_rate) / Decimal("100"))
    return pf_ee, pf_er


def calculate_esi(
    gross_pay: Decimal | int | float | str,
    monthly_fixed_gross: Decimal | int | float | str,
    pf_or_esi_applicable: bool,
    esi_ee_rate: Decimal = Decimal("0.75"),
    esi_er_rate: Decimal = Decimal("3.25"),
    esi_wage_limit: Decimal = Decimal("21000.0"),
) -> tuple[Decimal, Decimal]:
    """Rule 4 (Employees' State Insurance - ESI):
    Applies to permanent staff whose current monthly_fixed_gross <= 21,000:
      esi_employee = round_half_up(gross_pay * 0.75%)
      esi_employer = round_half_up(gross_pay * 3.25%)
    """
    if not pf_or_esi_applicable or to_dec(monthly_fixed_gross) > to_dec(esi_wage_limit):
        return Decimal("0.00"), Decimal("0.00")

    gross = to_dec(gross_pay)
    esi_ee = round_money(gross * to_dec(esi_ee_rate) / Decimal("100"))
    esi_er = round_money(gross * to_dec(esi_er_rate) / Decimal("100"))
    return esi_ee, esi_er


def calculate_professional_tax(
    gross_pay: Decimal | int | float | str,
    pt_threshold: Decimal = Decimal("25000.0"),
    pt_monthly: Decimal = Decimal("200.00"),
) -> Decimal:
    """Rule 5 (Professional Tax - PT):
    INR 200.00 per month when monthly gross_pay >= 25,000; otherwise 0.00.
    """
    if to_dec(gross_pay) >= to_dec(pt_threshold):
        return round_money(pt_monthly)
    return Decimal("0.00")


def calculate_annual_slab_tax(
    taxable_income: Decimal | int | float | str,
    slabs: list[dict[str, Any]] | None = None,
    rebate_threshold: Decimal = Decimal("1200000.00"),
) -> Decimal:
    """Compute annual slab tax before cess, applying Section 87A rebate up to 12,00,000
    and marginal relief just above 12,00,000.
    """
    taxable = to_dec(taxable_income)
    rebate_lim = to_dec(rebate_threshold)
    if taxable <= rebate_lim:
        return Decimal("0.00")

    active_slabs = slabs or DEFAULT_TAX_SLABS
    tax = Decimal("0.00")
    for s in active_slabs:
        low = to_dec(s["income_from"])
        high = to_dec(s["income_to"]) if s.get("income_to") is not None else None
        rate = to_dec(s["rate_percent"]) / Decimal("100")
        if taxable > low:
            band_income = (min(taxable, high) - low) if high is not None else (taxable - low)
            tax += band_income * rate

    # Marginal relief above rebate_threshold
    excess = taxable - rebate_lim
    if tax > excess:
        tax = excess
    return tax


def calculate_monthly_tds(
    monthly_fixed_gross: Decimal | int | float | str,
    payable_days: Decimal | int | float | str,
    calendar_days: int,
    variable_pay: Decimal | int | float | str = Decimal("0.00"),
    overtime_pay: Decimal | int | float | str = Decimal("0.00"),
    standard_deduction: Decimal = Decimal("75000.00"),
    rebate_threshold: Decimal = Decimal("1200000.00"),
    cess_percent: Decimal = Decimal("4.0"),
    slabs: list[dict[str, Any]] | None = None,
) -> Decimal:
    """Rule 6 (Income Tax Deducted at Source - TDS):
    1. Annual regular taxable income = (monthly_fixed_gross * 12) - standard_deduction (75,000).
    2. Annual base tax with 4% cess is divided by 12 and prorated by (payable_days / calendar_days),
       rounded half-up to 2 decimals.
    3. One-time monthly variable_pay and overtime_pay are taxed at their marginal annual slab impact
       plus 4% cess, rounded half-up to 2 decimals.
    """
    mfg = to_dec(monthly_fixed_gross)
    if mfg <= Decimal("0.00"):
        return Decimal("0.00")

    pay_days = to_dec(payable_days)
    cal_days = to_dec(calendar_days)
    vp = to_dec(variable_pay)
    ot = to_dec(overtime_pay)
    std_ded = to_dec(standard_deduction)
    cess_mult = Decimal("1") + (to_dec(cess_percent) / Decimal("100"))

    annual_base_taxable = (mfg * Decimal("12")) - std_ded
    annual_base_tax = calculate_annual_slab_tax(annual_base_taxable, slabs=slabs, rebate_threshold=rebate_threshold) * cess_mult
    monthly_base_tax = annual_base_tax / Decimal("12")
    prorated_base_tds = round_money(monthly_base_tax * (pay_days / cal_days))

    extra_pay = vp + ot
    if extra_pay > Decimal("0.00"):
        annual_total_taxable = annual_base_taxable + extra_pay
        annual_total_tax = (
            calculate_annual_slab_tax(annual_total_taxable, slabs=slabs, rebate_threshold=rebate_threshold) * cess_mult
        )
        extra_tds = round_money(annual_total_tax - annual_base_tax)
    else:
        extra_tds = Decimal("0.00")

    return round_money(prorated_base_tds + extra_tds)


def calculate_employee_month(
    employee_id: str,
    period_start: date,
    period_end: date,
    components: dict[str, Decimal | int | float | str],
    hire_date: date,
    exit_date: date | None = None,
    lop_days: Decimal | int | float | str = Decimal("0.00"),
    raw_overtime_hours: Decimal | int | float | str = Decimal("0.00"),
    overtime_eligible: bool = False,
    pf_applicable: bool = True,
    variable_pay: Decimal | int | float | str = Decimal("0.00"),
    variable_pay_type: str | None = None,
    other_deductions: Decimal | int | float | str = Decimal("0.00"),
    department_id: str = "",
    role_id: str = "",
    run_id: str | None = None,
    days_employed_override: int | None = None,
    slabs: list[dict[str, Any]] | None = None,
    standard_deduction: Decimal = Decimal("75000.00"),
    rebate_threshold: Decimal = Decimal("1200000.00"),
    cess_percent: Decimal = Decimal("4.0"),
) -> dict[str, Any]:
    """Pure function: computes every payslip number from gross to net pay for an employee-month."""
    calendar_days = (period_end - period_start).days + 1
    days_employed = (
        days_employed_override
        if days_employed_override is not None
        else calculate_days_employed(period_start, period_end, hire_date, exit_date)
    )
    lop_dec = round_money(lop_days)

    prorated = calculate_prorated_components(
        components=components,
        calendar_days=calendar_days,
        days_employed=days_employed,
        lop_days=lop_dec,
    )
    payable_days = prorated["payable_days"]
    mfg = prorated["monthly_fixed_gross"]
    earned_fixed_pay = prorated["earned_fixed_pay"]

    overtime_hours_paid, overtime_pay = calculate_overtime_pay(
        monthly_fixed_gross=mfg,
        raw_overtime_hours=raw_overtime_hours,
        overtime_eligible=overtime_eligible,
    )

    vp_dec = round_money(variable_pay)
    gross_pay = round_money(earned_fixed_pay + overtime_pay + vp_dec)

    pf_employee, pf_employer = calculate_pf(
        earned_basic=prorated["basic"],
        pf_applicable=pf_applicable,
    )
    esi_employee, esi_employer = calculate_esi(
        gross_pay=gross_pay,
        monthly_fixed_gross=mfg,
        pf_or_esi_applicable=pf_applicable,
    )
    professional_tax = calculate_professional_tax(gross_pay=gross_pay)
    tds = calculate_monthly_tds(
        monthly_fixed_gross=mfg,
        payable_days=payable_days,
        calendar_days=calendar_days,
        variable_pay=vp_dec,
        overtime_pay=overtime_pay,
        standard_deduction=standard_deduction,
        rebate_threshold=rebate_threshold,
        cess_percent=cess_percent,
        slabs=slabs,
    )
    other_ded_dec = round_money(other_deductions)

    total_deductions = round_money(pf_employee + esi_employee + professional_tax + tds + other_ded_dec)
    net_pay = round_money(gross_pay - total_deductions)
    employer_cost = round_money(gross_pay + pf_employer + esi_employer)

    computed_run_id = run_id or f"PR-{period_start.strftime('%Y-%m')}"

    return {
        "run_id": computed_run_id,
        "employee_id": employee_id,
        "period_start": period_start,
        "period_end": period_end,
        "department_id": department_id,
        "role_id": role_id,
        "calendar_days": calendar_days,
        "days_employed": days_employed,
        "lop_days": lop_dec,
        "payable_days": payable_days,
        "monthly_fixed_gross": mfg,
        "basic": prorated["basic"],
        "hra": prorated["hra"],
        "conveyance": prorated["conveyance"],
        "medical": prorated["medical"],
        "special_allowance": prorated["special_allowance"],
        "earned_fixed_pay": earned_fixed_pay,
        "overtime_hours_paid": overtime_hours_paid,
        "overtime_pay": overtime_pay,
        "variable_pay": vp_dec,
        "variable_pay_type": variable_pay_type,
        "gross_pay": gross_pay,
        "pf_employee": pf_employee,
        "esi_employee": esi_employee,
        "professional_tax": professional_tax,
        "tds": tds,
        "other_deductions": other_ded_dec,
        "total_deductions": total_deductions,
        "net_pay": net_pay,
        "pf_employer": pf_employer,
        "esi_employer": esi_employer,
        "employer_cost": employer_cost,
        "calculation_note": "LOP on calendar-day basis; OT 2x hourly (cap 50h)",
    }


def calculate_employee_month_from_db(
    session: Session,
    employee_id: str,
    month: str,
    variable_pay: Decimal = Decimal("0.00"),
    variable_pay_type: str | None = None,
    other_deductions: Decimal = Decimal("0.00"),
) -> dict[str, Any]:
    """Load employee, role, salary structure, attendance summary, and tax slabs from DB and run calculate_employee_month()."""
    emp = session.get(Employee, employee_id)
    if not emp:
        raise NotFoundError(f"Employee '{employee_id}' not found")

    try:
        parts = month.strip().split("-")
        year, mon = int(parts[0]), int(parts[1])
        _, last_day = calendar.monthrange(year, mon)
        p_start = date(year, mon, 1)
        p_end = date(year, mon, last_day)
    except Exception as exc:
        raise ValidationError(f"Invalid month '{month}'. Expected 'YYYY-MM'.") from exc

    # Fetch active salary structure for period_start (or period_end if joined mid-month)
    structs = list(
        session.scalars(
            select(SalaryStructure).where(
                SalaryStructure.employee_id == employee_id,
                SalaryStructure.effective_from <= p_end,
                or_(
                    SalaryStructure.effective_to.is_(None),
                    SalaryStructure.effective_to >= p_start,
                ),
            )
        ).all()
    )
    if not structs:
        raise NotFoundError(f"No active salary structure found for {employee_id} in {month}")

    comp_map = {s.component_id: Decimal(str(s.monthly_amount)) for s in structs}
    role = session.get(Role, emp.role_id)
    ot_eligible = bool(role.overtime_eligible) if role else False
    pf_applicable = emp.employment_type == "Permanent"

    att_sum = monthly_summary(session, employee_id, month)

    fy = f"FY{year}-{str(year + 1)[-2:]}" if mon >= 4 else f"FY{year - 1}-{str(year)[-2:]}"
    db_slabs = list(
        session.scalars(
            select(TaxSlab)
            .where(TaxSlab.financial_year == fy)
            .order_by(TaxSlab.income_from)
        ).all()
    )
    slabs_list = (
        [
            {
                "income_from": Decimal(str(s.income_from)),
                "income_to": Decimal(str(s.income_to)) if s.income_to is not None else None,
                "rate_percent": Decimal(str(s.rate_percent)),
            }
            for s in db_slabs
        ]
        if db_slabs
        else None
    )

    return calculate_employee_month(
        employee_id=employee_id,
        period_start=p_start,
        period_end=p_end,
        components=comp_map,
        hire_date=emp.hire_date,
        exit_date=emp.exit_date,
        lop_days=att_sum["lop_days"],
        raw_overtime_hours=att_sum["overtime_hours"],
        overtime_eligible=ot_eligible,
        pf_applicable=pf_applicable,
        variable_pay=variable_pay,
        variable_pay_type=variable_pay_type,
        other_deductions=other_deductions,
        department_id=emp.department_id,
        role_id=emp.role_id,
        run_id=f"PR-{month}",
        slabs=slabs_list,
    )
