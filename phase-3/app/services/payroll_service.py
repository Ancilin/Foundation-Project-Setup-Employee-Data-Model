"""Payroll calculation engine (LF-07): pure functions for gross-to-net pay with Decimal ROUND_HALF_UP."""

import calendar
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
import uuid
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.employee import Employee
from app.models.ledger import JournalEntry, JournalLine
from app.models.payroll import PayrollItem, PayrollRun, StatutoryRate, TaxParameter, TaxSlab
from app.models.role import Role
from app.models.salary import SalaryStructure
from app.services.attendance_service import monthly_summary
from app.services.ledger_service import (
    create_journal_entry,
    get_journal_entry_with_lines,
    post_payroll_run_to_ledger,
    reverse_journal_entry,
)

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
    s_full = to_dec(components.get("SPECIAL", components.get("SPECIAL_ALLOWANCE", components.get("SPEC", 0))))

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


def calculate_annual_tax_breakdown(
    monthly_fixed_gross: Decimal | int | float | str,
    payable_days: Decimal | int | float | str | None = None,
    calendar_days: int = 30,
    variable_pay: Decimal | int | float | str = Decimal("0.00"),
    overtime_pay: Decimal | int | float | str = Decimal("0.00"),
    standard_deduction: Decimal = Decimal("75000.00"),
    rebate_threshold: Decimal = Decimal("1200000.00"),
    cess_percent: Decimal = Decimal("4.0"),
    slabs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return full step-by-step annual tax breakdown:
    annual taxable income, slab-by-slab tax, Section 87A rebate / marginal relief,
    4% health & education cess, annual total tax, and monthly TDS (/ 12).
    """
    mfg = to_dec(monthly_fixed_gross)
    cal_days = to_dec(calendar_days if calendar_days > 0 else 30)
    pay_days = to_dec(payable_days) if payable_days is not None else cal_days
    std_ded = to_dec(standard_deduction)
    rebate_lim = to_dec(rebate_threshold)
    cess_pct = to_dec(cess_percent)

    annual_gross = round_money(mfg * Decimal("12"))
    annual_taxable = max(Decimal("0.00"), round_money(annual_gross - std_ded))

    active_slabs = slabs or DEFAULT_TAX_SLABS
    slab_breakdown: list[dict[str, Any]] = []
    raw_slab_tax = Decimal("0.00")

    for s in active_slabs:
        low = to_dec(s["income_from"])
        high = to_dec(s["income_to"]) if s.get("income_to") is not None else None
        rate_pct = to_dec(s["rate_percent"])
        rate = rate_pct / Decimal("100")
        if annual_taxable > low:
            band_income = (min(annual_taxable, high) - low) if high is not None else (annual_taxable - low)
        else:
            band_income = Decimal("0.00")
        band_tax = round_money(band_income * rate)
        raw_slab_tax += band_income * rate
        slab_breakdown.append(
            {
                "slab_id": s.get("slab_id"),
                "income_from": round_money(low),
                "income_to": round_money(high) if high is not None else None,
                "rate_percent": round_money(rate_pct),
                "taxable_in_slab": round_money(band_income),
                "tax_in_slab": band_tax,
            }
        )

    raw_slab_tax_rounded = round_money(raw_slab_tax)
    tax_after_rebate_exact = calculate_annual_slab_tax(
        annual_taxable,
        slabs=active_slabs,
        rebate_threshold=rebate_lim,
    )
    rebate_amount = round_money(max(Decimal("0.00"), raw_slab_tax - tax_after_rebate_exact))
    tax_after_rebate = round_money(tax_after_rebate_exact)
    cess_amount = round_money(tax_after_rebate_exact * (cess_pct / Decimal("100")))
    annual_total_tax = round_money(tax_after_rebate_exact * (Decimal("1") + cess_pct / Decimal("100")))

    monthly_tds = calculate_monthly_tds(
        monthly_fixed_gross=mfg,
        payable_days=pay_days,
        calendar_days=int(cal_days),
        variable_pay=variable_pay,
        overtime_pay=overtime_pay,
        standard_deduction=std_ded,
        rebate_threshold=rebate_lim,
        cess_percent=cess_pct,
        slabs=active_slabs,
    )

    return {
        "monthly_fixed_gross": round_money(mfg),
        "annual_gross_income": annual_gross,
        "standard_deduction": round_money(std_ded),
        "annual_taxable_income": annual_taxable,
        "rebate_threshold": round_money(rebate_lim),
        "raw_slab_tax": raw_slab_tax_rounded,
        "rebate_87a_amount": rebate_amount,
        "tax_after_rebate": tax_after_rebate,
        "cess_percent": round_money(cess_pct),
        "cess_amount": cess_amount,
        "annual_total_tax": annual_total_tax,
        "monthly_tds": monthly_tds,
        "slab_breakdown": slab_breakdown,
    }


def load_tax_and_statutory_rules_from_db(
    session: Session,
    period_start: date,
    period_end: date,
    regime: str = "NEW",
) -> dict[str, Any]:
    """Load all configurable tax slabs, tax parameters, and statutory rates from the database
    for the financial year and effective date of [period_start, period_end].
    Falls back to standard defaults only when tables are unseeded in isolated unit tests.
    """
    fy = (
        f"FY{period_start.year}-{str(period_start.year + 1)[-2:]}"
        if period_start.month >= 4
        else f"FY{period_start.year - 1}-{str(period_start.year)[-2:]}"
    )
    db_slabs = list(
        session.scalars(
            select(TaxSlab)
            .where(
                TaxSlab.financial_year == fy,
                TaxSlab.regime == regime.upper(),
                TaxSlab.effective_from <= period_end,
            )
            .order_by(TaxSlab.income_from)
        ).all()
    )
    if not db_slabs:
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
                "slab_id": s.slab_id,
                "income_from": Decimal(str(s.income_from)),
                "income_to": Decimal(str(s.income_to)) if s.income_to is not None else None,
                "rate_percent": Decimal(str(s.rate_percent)),
            }
            for s in db_slabs
        ]
        if db_slabs
        else None
    )

    tp_rows = session.scalars(select(TaxParameter)).all()
    tp_map = {r.parameter.strip(): Decimal(str(r.value)) for r in tp_rows}

    sr_rows = session.scalars(
        select(StatutoryRate).where(StatutoryRate.effective_from <= period_end)
    ).all()
    if not sr_rows:
        sr_rows = session.scalars(select(StatutoryRate)).all()
    sr_map = {r.parameter.strip(): Decimal(str(r.value)) for r in sr_rows}

    return {
        "financial_year": fy,
        "regime": regime.upper(),
        "slabs": slabs_list,
        "standard_deduction": tp_map.get("standard_deduction", Decimal("75000.00")),
        "rebate_threshold": tp_map.get("rebate_threshold_taxable", Decimal("1200000.00")),
        "cess_percent": tp_map.get("health_education_cess_percent", Decimal("4.0")),
        "pf_ee_rate": sr_map.get("PF_EMPLOYEE_RATE", Decimal("12.0")),
        "pf_er_rate": sr_map.get("PF_EMPLOYER_RATE", Decimal("12.0")),
        "pf_wage_ceiling": sr_map.get("PF_WAGE_CEILING", Decimal("15000.0")),
        "esi_ee_rate": sr_map.get("ESI_EMPLOYEE_RATE", Decimal("0.75")),
        "esi_er_rate": sr_map.get("ESI_EMPLOYER_RATE", Decimal("3.25")),
        "esi_wage_limit": sr_map.get("ESI_WAGE_LIMIT", Decimal("21000.0")),
        "pt_monthly": sr_map.get("PT_MONTHLY", Decimal("200.00")),
        "pt_threshold": sr_map.get("PT_GROSS_THRESHOLD", Decimal("25000.0")),
        "ot_multiplier": sr_map.get("OT_MULTIPLIER", Decimal("2.0")),
        "ot_cap_hours": sr_map.get("OT_MONTHLY_CAP_HOURS", Decimal("50.0")),
        "working_hours_per_month": sr_map.get("WORKING_HOURS_PER_MONTH", Decimal("208.0")),
    }


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
    pf_ee_rate: Decimal = Decimal("12.0"),
    pf_er_rate: Decimal = Decimal("12.0"),
    pf_wage_ceiling: Decimal = Decimal("15000.0"),
    esi_ee_rate: Decimal = Decimal("0.75"),
    esi_er_rate: Decimal = Decimal("3.25"),
    esi_wage_limit: Decimal = Decimal("21000.0"),
    pt_monthly: Decimal = Decimal("200.00"),
    pt_threshold: Decimal = Decimal("25000.0"),
    ot_multiplier: Decimal = Decimal("2.0"),
    ot_cap_hours: Decimal = Decimal("50.0"),
    working_hours_per_month: Decimal = Decimal("208.0"),
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
        ot_multiplier=ot_multiplier,
        ot_cap_hours=ot_cap_hours,
        working_hours_per_month=working_hours_per_month,
    )

    vp_dec = round_money(variable_pay)
    gross_pay = round_money(earned_fixed_pay + overtime_pay + vp_dec)

    pf_employee, pf_employer = calculate_pf(
        earned_basic=prorated["basic"],
        pf_applicable=pf_applicable,
        pf_ee_rate=pf_ee_rate,
        pf_er_rate=pf_er_rate,
        pf_wage_ceiling=pf_wage_ceiling,
    )
    esi_employee, esi_employer = calculate_esi(
        gross_pay=gross_pay,
        monthly_fixed_gross=mfg,
        pf_or_esi_applicable=pf_applicable,
        esi_ee_rate=esi_ee_rate,
        esi_er_rate=esi_er_rate,
        esi_wage_limit=esi_wage_limit,
    )
    professional_tax = calculate_professional_tax(
        gross_pay=gross_pay,
        pt_threshold=pt_threshold,
        pt_monthly=pt_monthly,
    )
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
    rules = load_tax_and_statutory_rules_from_db(session, p_start, p_end)

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
        slabs=rules["slabs"],
        standard_deduction=rules["standard_deduction"],
        rebate_threshold=rules["rebate_threshold"],
        cess_percent=rules["cess_percent"],
        pf_ee_rate=rules["pf_ee_rate"],
        pf_er_rate=rules["pf_er_rate"],
        pf_wage_ceiling=rules["pf_wage_ceiling"],
        esi_ee_rate=rules["esi_ee_rate"],
        esi_er_rate=rules["esi_er_rate"],
        esi_wage_limit=rules["esi_wage_limit"],
        pt_monthly=rules["pt_monthly"],
        pt_threshold=rules["pt_threshold"],
        ot_multiplier=rules["ot_multiplier"],
        ot_cap_hours=rules["ot_cap_hours"],
        working_hours_per_month=rules["working_hours_per_month"],
    )


# ==============================================================================
# Task 12 (LF-12): Payroll Run Workflow, Idempotent Ledger Posting & Reversal
# ==============================================================================


def _parse_month_bounds(month: str) -> tuple[date, date]:
    try:
        parts = month.strip().split("-")
        year, mon = int(parts[0]), int(parts[1])
        _, last_day = calendar.monthrange(year, mon)
        return date(year, mon, 1), date(year, mon, last_day)
    except Exception as exc:
        raise ValidationError(f"Invalid month '{month}'. Expected 'YYYY-MM'.") from exc


def list_payroll_runs(session: Session) -> list[PayrollRun]:
    """List all payroll runs ordered by period_start and run_id."""
    return list(
        session.scalars(
            select(PayrollRun).order_by(PayrollRun.period_start, PayrollRun.run_id)
        ).all()
    )


def get_payroll_run_with_details(session: Session, run_id: str) -> dict[str, Any]:
    """Retrieve a payroll run along with its linked journal entry and employer-cost reconciliation."""
    pr = session.get(PayrollRun, run_id)
    if not pr:
        raise NotFoundError(f"Payroll run '{run_id}' not found")

    je_data = None
    ledger_emp_cost = Decimal("0.00")
    if pr.journal_entry_id:
        je_obj = session.get(JournalEntry, pr.journal_entry_id)
        if je_obj is not None:
            je_data = get_journal_entry_with_lines(session, pr.journal_entry_id)
            ledger_emp_cost = round_money(
                sum(
                    (
                        to_dec(line.debit) - to_dec(line.credit)
                        for line in je_data["lines"]
                        if 5001 <= int(line.account_code) <= 5005
                    ),
                    Decimal("0.00"),
                )
            )

    run_emp_cost = round_money(pr.total_employer_cost)
    diff = round_money(run_emp_cost - ledger_emp_cost) if je_data else Decimal("0.00")

    return {
        "run_id": pr.run_id,
        "period_start": pr.period_start,
        "period_end": pr.period_end,
        "pay_date": pr.pay_date,
        "employees_paid": pr.employees_paid,
        "total_gross": round_money(pr.total_gross),
        "total_deductions": round_money(pr.total_deductions),
        "total_net": round_money(pr.total_net),
        "total_employer_contributions": round_money(pr.total_employer_contributions),
        "total_employer_cost": run_emp_cost,
        "status": pr.status,
        "run_by": pr.run_by,
        "approved_by": pr.approved_by,
        "approved_at": pr.approved_at,
        "idempotency_key": pr.idempotency_key,
        "journal_entry_id": pr.journal_entry_id,
        "calculation_version": pr.calculation_version,
        "ledger_employer_cost_5001_5005": ledger_emp_cost,
        "employer_cost_difference": diff,
        "journal_entry": je_data,
    }


def create_payroll_run(
    session: Session,
    month: str,
    run_id: str | None = None,
    pay_date: date | None = None,
    run_by: str = "U-0237",
    idempotency_key: str | None = None,
) -> PayrollRun:
    """Create a payroll run in DRAFT status (idempotent by run_id and idempotency_key)."""
    p_start, p_end = _parse_month_bounds(month)
    final_run_id = run_id.strip() if run_id and run_id.strip() else f"PR-{month.strip()}"
    final_idem_key = (
        idempotency_key.strip()
        if idempotency_key and idempotency_key.strip()
        else f"payroll:{month.strip()}:ZNT"
    )

    # Idempotency check by run_id or idempotency_key
    existing_by_id = session.get(PayrollRun, final_run_id)
    if existing_by_id is not None:
        return existing_by_id

    existing_by_key = session.scalar(
        select(PayrollRun).where(PayrollRun.idempotency_key == final_idem_key)
    )
    if existing_by_key is not None:
        return existing_by_key

    pr = PayrollRun(
        run_id=final_run_id,
        period_start=p_start,
        period_end=p_end,
        pay_date=pay_date,
        employees_paid=0,
        total_gross=Decimal("0.00"),
        total_deductions=Decimal("0.00"),
        total_net=Decimal("0.00"),
        total_employer_contributions=Decimal("0.00"),
        total_employer_cost=Decimal("0.00"),
        status="DRAFT",
        run_by=run_by.strip() if run_by else "U-0237",
        approved_by=None,
        approved_at=None,
        idempotency_key=final_idem_key,
        journal_entry_id=None,
        calculation_version="payroll-engine-1.0",
    )
    session.add(pr)
    session.commit()
    session.refresh(pr)
    return pr


def process_payroll_run(
    session: Session,
    run_id: str,
    run_by: str | None = None,
    allow_rerun: bool = False,
) -> PayrollRun:
    """Process a DRAFT (or PROCESSED) payroll run by running the Task 7 calculation engine
    for every eligible employee in the run's month, updating PayrollItem rows and run totals,
    and transitioning status to PROCESSED.
    Refuses to re-process an already APPROVED or PAID run unless allow_rerun=True is explicitly passed by an Admin.
    """
    pr = session.get(PayrollRun, run_id)
    if not pr:
        raise NotFoundError(f"Payroll run '{run_id}' not found")

    original_status = pr.status
    if not allow_rerun and pr.status in ("APPROVED", "POSTED - PAYMENT PENDING", "PAID"):
        raise ConflictError(
            f"Payroll run '{run_id}' has status '{pr.status}' and is locked. "
            "Reverse the run before re-processing.",
            error_code="RUN_ALREADY_APPROVED",
        )
    if pr.status == "REVERSED":
        raise ConflictError(
            f"Payroll run '{run_id}' has been REVERSED and cannot be re-processed.",
            error_code="RUN_REVERSED",
        )

    p_start = pr.period_start
    p_end = pr.period_end
    month_str = p_start.strftime("%Y-%m")

    existing_items = list(
        session.scalars(
            select(PayrollItem)
            .where(PayrollItem.run_id == run_id)
            .order_by(PayrollItem.employee_id)
        ).all()
    )

    rules = load_tax_and_statutory_rules_from_db(session, p_start, p_end)

    if existing_items:
        # Re-verify/process each existing PayrollItem through Task 7 calculate_employee_month()
        for item in existing_items:
            emp = session.get(Employee, item.employee_id)
            if not emp:
                continue
            structs = list(
                session.scalars(
                    select(SalaryStructure).where(
                        SalaryStructure.employee_id == item.employee_id,
                        SalaryStructure.effective_from <= p_end,
                        or_(
                            SalaryStructure.effective_to.is_(None),
                            SalaryStructure.effective_to >= p_start,
                        ),
                    )
                ).all()
            )
            if structs:
                comp_map = {s.component_id: Decimal(str(s.monthly_amount)) for s in structs}
            else:
                comp_map = {
                    "BASIC": to_dec(item.basic),
                    "HRA": to_dec(item.hra),
                    "CONV": to_dec(item.conveyance),
                    "MED": to_dec(item.medical),
                    "SPEC": to_dec(item.special_allowance),
                }
            role = session.get(Role, item.role_id or emp.role_id)
            ot_eligible = bool(role.overtime_eligible) if role else (to_dec(item.overtime_pay) > Decimal("0.00"))
            pf_applicable = emp.employment_type == "Permanent"

            calc = calculate_employee_month(
                employee_id=item.employee_id,
                period_start=p_start,
                period_end=p_end,
                components=comp_map,
                hire_date=emp.hire_date,
                exit_date=emp.exit_date,
                lop_days=item.lop_days,
                raw_overtime_hours=item.overtime_hours_paid,
                overtime_eligible=ot_eligible,
                pf_applicable=pf_applicable,
                variable_pay=item.variable_pay,
                variable_pay_type=item.variable_pay_type,
                other_deductions=item.other_deductions,
                department_id=item.department_id,
                role_id=item.role_id,
                run_id=run_id,
                days_employed_override=item.days_employed,
                slabs=rules["slabs"],
                standard_deduction=rules["standard_deduction"],
                rebate_threshold=rules["rebate_threshold"],
                cess_percent=rules["cess_percent"],
                pf_ee_rate=rules["pf_ee_rate"],
                pf_er_rate=rules["pf_er_rate"],
                pf_wage_ceiling=rules["pf_wage_ceiling"],
                esi_ee_rate=rules["esi_ee_rate"],
                esi_er_rate=rules["esi_er_rate"],
                esi_wage_limit=rules["esi_wage_limit"],
                pt_monthly=rules["pt_monthly"],
                pt_threshold=rules["pt_threshold"],
                ot_multiplier=rules["ot_multiplier"],
                ot_cap_hours=rules["ot_cap_hours"],
                working_hours_per_month=rules["working_hours_per_month"],
            )
            item.gross_pay = calc["gross_pay"]
            item.pf_employee = calc["pf_employee"]
            item.esi_employee = calc["esi_employee"]
            item.professional_tax = calc["professional_tax"]
            item.tds = calc["tds"]
            item.total_deductions = calc["total_deductions"]
            item.net_pay = calc["net_pay"]
            item.pf_employer = calc["pf_employer"]
            item.esi_employer = calc["esi_employer"]
            item.employer_cost = calc["employer_cost"]
        processed_items = existing_items
    else:
        # Compute fresh PayrollItems for all active employees in [p_start, p_end] using Task 7 engine
        eligible_emps = list(
            session.scalars(
                select(Employee)
                .where(
                    Employee.hire_date <= p_end,
                    or_(Employee.exit_date.is_(None), Employee.exit_date >= p_start),
                )
                .order_by(Employee.employee_id)
            ).all()
        )
        base_count = (session.scalar(select(func.count(PayrollItem.payroll_item_id))) or 0) + 1
        processed_items = []
        seq = 0
        for emp in eligible_emps:
            structs = list(
                session.scalars(
                    select(SalaryStructure).where(
                        SalaryStructure.employee_id == emp.employee_id,
                        SalaryStructure.effective_from <= p_end,
                        or_(
                            SalaryStructure.effective_to.is_(None),
                            SalaryStructure.effective_to >= p_start,
                        ),
                    )
                ).all()
            )
            if not structs:
                continue

            calc = calculate_employee_month_from_db(session, emp.employee_id, month_str)
            seq += 1
            pi_id = f"PI-{base_count + seq:06d}"
            if session.get(PayrollItem, pi_id) is not None:
                pi_id = f"PI-{uuid.uuid4().hex[:6].upper()}"

            new_item = PayrollItem(
                payroll_item_id=pi_id,
                run_id=run_id,
                employee_id=emp.employee_id,
                period_start=p_start,
                period_end=p_end,
                department_id=calc["department_id"],
                role_id=calc["role_id"],
                calendar_days=calc["calendar_days"],
                days_employed=calc["days_employed"],
                lop_days=calc["lop_days"],
                payable_days=calc["payable_days"],
                monthly_fixed_gross=calc["monthly_fixed_gross"],
                basic=calc["basic"],
                hra=calc["hra"],
                conveyance=calc["conveyance"],
                medical=calc["medical"],
                special_allowance=calc["special_allowance"],
                earned_fixed_pay=calc["earned_fixed_pay"],
                overtime_hours_paid=calc["overtime_hours_paid"],
                overtime_pay=calc["overtime_pay"],
                variable_pay=calc["variable_pay"],
                variable_pay_type=calc["variable_pay_type"],
                gross_pay=calc["gross_pay"],
                pf_employee=calc["pf_employee"],
                esi_employee=calc["esi_employee"],
                professional_tax=calc["professional_tax"],
                tds=calc["tds"],
                other_deductions=calc["other_deductions"],
                total_deductions=calc["total_deductions"],
                net_pay=calc["net_pay"],
                pf_employer=calc["pf_employer"],
                esi_employer=calc["esi_employer"],
                employer_cost=calc["employer_cost"],
                calculation_note=calc["calculation_note"],
            )
            session.add(new_item)
            processed_items.append(new_item)

    if not processed_items:
        raise ValidationError(
            f"No eligible employees with active salary structures found to process payroll run '{run_id}'.",
            error_code="EMPTY_PAYROLL_RUN",
        )

    tot_gross = round_money(sum((to_dec(i.gross_pay) for i in processed_items), Decimal("0.00")))
    tot_ded = round_money(sum((to_dec(i.total_deductions) for i in processed_items), Decimal("0.00")))
    tot_net = round_money(sum((to_dec(i.net_pay) for i in processed_items), Decimal("0.00")))
    tot_er_contrib = round_money(
        sum((to_dec(i.pf_employer) + to_dec(i.esi_employer) for i in processed_items), Decimal("0.00"))
    )
    tot_er_cost = round_money(sum((to_dec(i.employer_cost) for i in processed_items), Decimal("0.00")))

    pr.employees_paid = len(processed_items)
    pr.total_gross = tot_gross
    pr.total_deductions = tot_ded
    pr.total_net = tot_net
    pr.total_employer_contributions = tot_er_contrib
    pr.total_employer_cost = tot_er_cost
    pr.status = original_status if (allow_rerun and original_status in ("APPROVED", "POSTED - PAYMENT PENDING", "PAID")) else "PROCESSED"
    if run_by and run_by.strip():
        pr.run_by = run_by.strip()
    pr.calculation_version = "payroll-engine-1.0"

    session.commit()
    session.refresh(pr)
    return pr


def approve_payroll_run(
    session: Session,
    run_id: str,
    approved_by: str = "U-0099",
    idempotency_key: str | None = None,
    simulate_ledger_failure: bool = False,
) -> dict[str, Any]:
    """Approve a PROCESSED payroll run and post ONE journal entry to the ledger atomically.
    - Idempotency: If the run (or its idempotency_key) is already approved and posted, a double click
      returns the existing run and journal entry without posting a second time.
    - Separation of duties: approved_by cannot equal run_by.
    - Atomic failure rule: If ledger posting fails halfway through, the transaction savepoint rolls back
      both the ledger lines and the run status so the run remains PROCESSED with journal_entry_id=None.
    """
    pr = session.get(PayrollRun, run_id)
    if not pr:
        raise NotFoundError(f"Payroll run '{run_id}' not found")

    if pr.status == "REVERSED":
        raise ConflictError(
            f"Payroll run '{run_id}' has been REVERSED and cannot be approved.",
            error_code="RUN_REVERSED",
        )

    # 1. Idempotency check: if already posted, return existing posting (safe against double-clicks!)
    if pr.status in ("APPROVED", "POSTED - PAYMENT PENDING", "PAID") and pr.journal_entry_id:
        existing_je = session.get(JournalEntry, pr.journal_entry_id)
        if existing_je is not None:
            details = get_payroll_run_with_details(session, run_id)
            details["idempotent_replay"] = True
            return details

    existing_je_by_source = session.scalar(
        select(JournalEntry).where(
            JournalEntry.source_type == "PAYROLL_RUN",
            JournalEntry.source_id == run_id,
            JournalEntry.status == "POSTED",
        )
    )
    if existing_je_by_source is not None:
        rev = session.scalar(
            select(JournalEntry).where(
                JournalEntry.reversal_of_source_id == run_id,
                JournalEntry.source_id == f"REV-{existing_je_by_source.entry_id}",
                JournalEntry.status == "POSTED",
            )
        )
        if rev is None:
            pr.journal_entry_id = existing_je_by_source.entry_id
            if pr.status in ("DRAFT", "PROCESSED"):
                pr.status = "APPROVED"
            session.commit()
            details = get_payroll_run_with_details(session, run_id)
            details["idempotent_replay"] = True
            return details

    # 2. Must be PROCESSED before approval
    if pr.status == "DRAFT":
        raise ValidationError(
            f"Payroll run '{run_id}' is in DRAFT status. Process the run before approving.",
            error_code="RUN_NOT_PROCESSED",
        )

    # 3. Separation of duties check
    clean_approver = (approved_by or "U-0099").strip()
    if pr.run_by and clean_approver.upper() == pr.run_by.strip().upper():
        raise ValidationError(
            f"Separation of duties violation: user '{clean_approver}' ran payroll '{run_id}' and cannot approve it.",
            error_code="SEPARATION_OF_DUTIES_VIOLATION",
        )

    # 4. Atomic transaction: approve + post to ledger as one unit of work
    try:
        eff_idem_key = (
            idempotency_key.strip()
            if idempotency_key and idempotency_key.strip()
            else (pr.idempotency_key or f"payroll:{pr.period_start.strftime('%Y-%m')}:ZNT")
        )
        pr.idempotency_key = eff_idem_key
        pr.approved_by = clean_approver
        pr.approved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pr.status = "APPROVED"
        session.flush()

        if simulate_ledger_failure:
            raise RuntimeError("Simulated mid-flight ledger failure during payroll approval")

        je = post_payroll_run_to_ledger(
            session=session,
            run_id=run_id,
            created_by=clean_approver,
        )
        pr.journal_entry_id = je["entry_id"]
        session.commit()
    except Exception:
        session.rollback()
        raise

    details = get_payroll_run_with_details(session, run_id)
    details["idempotent_replay"] = False
    return details


def pay_payroll_run(
    session: Session,
    run_id: str,
    pay_date: date | None = None,
    paid_by: str = "U-0099",
) -> dict[str, Any]:
    """Mark an APPROVED payroll run as PAID and post the salary disbursement journal entry
    (Debit 2100 Salaries Payable / Credit 1001 Bank - Operating Account).
    """
    pr = session.get(PayrollRun, run_id)
    if not pr:
        raise NotFoundError(f"Payroll run '{run_id}' not found")

    if pr.status in ("DRAFT", "PROCESSED") or not pr.journal_entry_id:
        raise ValidationError(
            f"Payroll run '{run_id}' (status={pr.status}) cannot be paid before approval.",
            error_code="RUN_NOT_APPROVED",
        )
    if pr.status == "REVERSED":
        raise ConflictError(
            f"Payroll run '{run_id}' is REVERSED and cannot be paid.",
            error_code="RUN_REVERSED",
        )

    eff_pay_date = pay_date or pr.pay_date or (pr.period_end + calendar.timedelta(days=1) if hasattr(calendar, "timedelta") else date.today())

    # Check if SALARY_PAYMENT journal entry already exists for this run
    existing_pay_je = session.scalar(
        select(JournalEntry).where(
            JournalEntry.source_type == "SALARY_PAYMENT",
            JournalEntry.source_id == run_id,
            JournalEntry.status == "POSTED",
        )
    )
    if existing_pay_je is None:
        net_amt = round_money(pr.total_net)
        if net_amt > Decimal("0.00"):
            create_journal_entry(
                session=session,
                lines=[
                    {
                        "account_code": 2100,
                        "debit": net_amt,
                        "credit": Decimal("0.00"),
                        "cost_center_department_id": None,
                        "line_description": f"Salaries disbursed {run_id}",
                    },
                    {
                        "account_code": 1001,
                        "debit": Decimal("0.00"),
                        "credit": net_amt,
                        "cost_center_department_id": None,
                        "line_description": f"Bank transfer for payroll {run_id}",
                    },
                ],
                entry_date=eff_pay_date,
                description=f"Salary payment {run_id}",
                source_type="SALARY_PAYMENT",
                source_id=run_id,
                created_by=paid_by or "U-0099",
            )

    pr.pay_date = eff_pay_date
    pr.status = "PAID"
    session.commit()
    return get_payroll_run_with_details(session, run_id)


def reverse_payroll_run(
    session: Session,
    run_id: str,
    reversal_date: date | None = None,
    reversed_by: str = "U-0099",
    reason: str | None = None,
) -> dict[str, Any]:
    """Cancel/reverse a posted payroll run and post an official reversing journal entry
    that swaps all debits and credits of its PAYROLL_RUN ledger entry (and SALARY_PAYMENT if paid).
    """
    pr = session.get(PayrollRun, run_id)
    if not pr:
        raise NotFoundError(f"Payroll run '{run_id}' not found")

    if pr.status == "REVERSED":
        raise ConflictError(
            f"Payroll run '{run_id}' has already been reversed.",
            error_code="RUN_ALREADY_REVERSED",
        )

    if not pr.journal_entry_id:
        raise ValidationError(
            f"Payroll run '{run_id}' has not been posted to the ledger yet and cannot be reversed.",
            error_code="RUN_NOT_POSTED",
        )

    eff_rev_date = reversal_date or pr.period_end
    rev_desc = (
        f"Reversal of payroll {run_id}: {reason}"
        if reason
        else f"Reversal of Payroll posting {run_id} ({pr.journal_entry_id})"
    )

    rev_je = reverse_journal_entry(
        session=session,
        entry_id=pr.journal_entry_id,
        reversal_date=eff_rev_date,
        description=rev_desc,
        created_by=reversed_by or "U-0099",
    )

    # Also reverse salary payment entry if one was posted
    pay_je = session.scalar(
        select(JournalEntry).where(
            JournalEntry.source_type == "SALARY_PAYMENT",
            JournalEntry.source_id == run_id,
            JournalEntry.status == "POSTED",
        )
    )
    pay_rev_je_id = None
    if pay_je is not None:
        existing_pay_rev = session.scalar(
            select(JournalEntry).where(
                JournalEntry.source_id == f"REV-{pay_je.entry_id}",
                JournalEntry.status == "POSTED",
            )
        )
        if existing_pay_rev is None:
            pay_rev = reverse_journal_entry(
                session=session,
                entry_id=pay_je.entry_id,
                reversal_date=eff_rev_date,
                description=f"Reversal of Salary payment {run_id} ({pay_je.entry_id})",
                created_by=reversed_by or "U-0099",
            )
            pay_rev_je_id = pay_rev["entry_id"]

    pr.status = "REVERSED"
    session.commit()

    details = get_payroll_run_with_details(session, run_id)
    details["reversal_journal_entry_id"] = rev_je["entry_id"]
    details["payment_reversal_journal_entry_id"] = pay_rev_je_id
    details["reversal_journal_entry"] = rev_je
    return details


def reconcile_all_payroll_runs_with_ledger(session: Session) -> dict[str, Any]:
    """Reconcile all active payroll runs against accounts 5001..5005 in the double-entry ledger (Check 2)."""
    runs = list(
        session.scalars(
            select(PayrollRun)
            .where(PayrollRun.status != "REVERSED")
            .order_by(PayrollRun.period_start, PayrollRun.run_id)
        ).all()
    )

    stmt = (
        select(
            JournalEntry.source_id,
            JournalEntry.entry_id,
            func.coalesce(func.sum(JournalLine.debit - JournalLine.credit), 0),
        )
        .join(JournalLine, JournalLine.entry_id == JournalEntry.entry_id)
        .where(
            JournalEntry.source_type == "PAYROLL_RUN",
            JournalEntry.status == "POSTED",
            JournalLine.account_code.between(5001, 5005),
        )
        .group_by(JournalEntry.source_id, JournalEntry.entry_id)
    )
    ledger_by_run: dict[str, tuple[str, Decimal]] = {}
    for src_id, eid, net_dr in session.execute(stmt).all():
        ledger_by_run[str(src_id)] = (str(eid), round_money(net_dr))

    rows: list[dict[str, Any]] = []
    tot_run_cost = Decimal("0.00")
    tot_ledger_cost = Decimal("0.00")
    max_diff = Decimal("0.00")
    all_match = True

    for r in runs:
        run_cost = round_money(r.total_employer_cost)
        je_id, led_cost = ledger_by_run.get(r.run_id, (r.journal_entry_id or "", Decimal("0.00")))
        diff = round_money(run_cost - led_cost)
        matches = (
            diff == Decimal("0.00")
            and bool(r.journal_entry_id)
            and r.journal_entry_id == je_id
        )
        if not matches:
            all_match = False
        max_diff = max(max_diff, abs(diff))
        tot_run_cost = round_money(tot_run_cost + run_cost)
        tot_ledger_cost = round_money(tot_ledger_cost + led_cost)

        rows.append(
            {
                "run_id": r.run_id,
                "month": r.period_start.strftime("%Y-%m"),
                "status": r.status,
                "employees_paid": r.employees_paid,
                "idempotency_key": r.idempotency_key,
                "journal_entry_id": r.journal_entry_id,
                "total_gross": round_money(r.total_gross),
                "total_employer_contributions": round_money(r.total_employer_contributions),
                "run_employer_cost": run_cost,
                "ledger_accounts_5001_5005_debit": led_cost,
                "difference": diff,
                "matches": matches,
            }
        )

    return {
        "total_runs": len(rows),
        "all_months_match": all_match,
        "total_run_employer_cost": tot_run_cost,
        "total_ledger_employer_cost": tot_ledger_cost,
        "largest_monthly_difference": max_diff,
        "runs": rows,
    }
