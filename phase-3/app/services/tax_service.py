"""Configurable Tax Rules (Slabs, Parameters, Statutory Rates) & Monthly Statutory Reports (PF, ESI, TDS) Service (Task 14 / LF-14)."""

import calendar
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.employee import Employee
from app.models.payroll import PayrollItem, PayrollRun, StatutoryRate, TaxParameter, TaxSlab
from app.services.payroll_service import (
    calculate_annual_tax_breakdown,
    calculate_employee_month_from_db,
    load_tax_and_statutory_rules_from_db,
    process_payroll_run,
    round_money,
    to_dec,
)


def _normalize_month_and_run_id(month_or_run_id: str) -> tuple[str, str, date, date]:
    clean = month_or_run_id.strip()
    if clean.upper().startswith("PR-"):
        month_str = clean[3:]
    else:
        month_str = clean
    try:
        parts = month_str.split("-")
        year, mon = int(parts[0]), int(parts[1])
        _, last_day = calendar.monthrange(year, mon)
        p_start = date(year, mon, 1)
        p_end = date(year, mon, last_day)
        canonical_month = f"{year:04d}-{mon:02d}"
        return canonical_month, f"PR-{canonical_month}", p_start, p_end
    except Exception as exc:
        raise ValidationError(f"Invalid month or run_id '{month_or_run_id}'. Expected 'YYYY-MM' or 'PR-YYYY-MM'.") from exc


# ==============================================================================
# 1. Configurable Tax Slabs, Tax Parameters & Statutory Rates CRUD
# ==============================================================================


def list_tax_slabs(
    session: Session,
    financial_year: str | None = None,
    regime: str | None = None,
) -> list[TaxSlab]:
    stmt = select(TaxSlab)
    if financial_year:
        stmt = stmt.where(TaxSlab.financial_year == financial_year.strip())
    if regime:
        stmt = stmt.where(TaxSlab.regime == regime.strip().upper())
    stmt = stmt.order_by(TaxSlab.financial_year, TaxSlab.regime, TaxSlab.income_from, TaxSlab.slab_id)
    return list(session.scalars(stmt).all())


def create_tax_slab(
    session: Session,
    slab_id: str,
    financial_year: str,
    income_from: Decimal,
    rate_percent: Decimal,
    effective_from: date,
    regime: str = "NEW",
    income_to: Decimal | None = None,
    note: str | None = None,
) -> TaxSlab:
    sid = slab_id.strip()
    if session.get(TaxSlab, sid) is not None:
        raise ConflictError(f"Tax slab '{sid}' already exists.", error_code="DUPLICATE_SLAB")
    if income_to is not None and to_dec(income_to) <= to_dec(income_from):
        raise ValidationError("income_to must be greater than income_from.")

    slab = TaxSlab(
        slab_id=sid,
        regime=regime.strip().upper(),
        financial_year=financial_year.strip(),
        income_from=round_money(income_from),
        income_to=round_money(income_to) if income_to is not None else None,
        rate_percent=round_money(rate_percent),
        effective_from=effective_from,
        note=note,
    )
    session.add(slab)
    session.commit()
    session.refresh(slab)
    return slab


def update_tax_slab(
    session: Session,
    slab_id: str,
    rate_percent: Decimal | None = None,
    income_from: Decimal | None = None,
    income_to: Decimal | None = None,
    effective_from: date | None = None,
    note: str | None = None,
) -> TaxSlab:
    slab = session.get(TaxSlab, slab_id.strip())
    if slab is None:
        raise NotFoundError(f"Tax slab '{slab_id}' not found.")

    if rate_percent is not None:
        if to_dec(rate_percent) < Decimal("0.00") or to_dec(rate_percent) > Decimal("100.00"):
            raise ValidationError("rate_percent must be between 0 and 100.")
        slab.rate_percent = round_money(rate_percent)
    if income_from is not None:
        slab.income_from = round_money(income_from)
    if income_to is not None:
        slab.income_to = round_money(income_to)
    if effective_from is not None:
        slab.effective_from = effective_from
    if note is not None:
        slab.note = note

    session.commit()
    session.refresh(slab)
    return slab


def list_tax_parameters(session: Session) -> list[TaxParameter]:
    return list(session.scalars(select(TaxParameter).order_by(TaxParameter.parameter)).all())


def update_tax_parameter(
    session: Session,
    parameter: str,
    value: Decimal,
    note: str | None = None,
) -> TaxParameter:
    tp = session.get(TaxParameter, parameter.strip())
    if tp is None:
        raise NotFoundError(f"Tax parameter '{parameter}' not found.")
    tp.value = round_money(value)
    if note is not None:
        tp.note = note
    session.commit()
    session.refresh(tp)
    return tp


def list_statutory_rates(session: Session) -> list[StatutoryRate]:
    return list(session.scalars(select(StatutoryRate).order_by(StatutoryRate.parameter)).all())


def update_statutory_rate(
    session: Session,
    parameter: str,
    value: Decimal,
    effective_from: date | None = None,
    note: str | None = None,
) -> StatutoryRate:
    sr = session.get(StatutoryRate, parameter.strip())
    if sr is None:
        raise NotFoundError(f"Statutory rate '{parameter}' not found.")
    sr.value = to_dec(value)
    if effective_from is not None:
        sr.effective_from = effective_from
    if note is not None:
        sr.note = note
    session.commit()
    session.refresh(sr)
    return sr


# ==============================================================================
# 2. Employee Annual Tax Breakdown & Slab Change Rerun Demonstration
# ==============================================================================


def get_employee_tax_breakdown(
    session: Session,
    employee_id: str,
    month: str,
) -> dict[str, Any]:
    """Compute the full annual tax breakdown (annual taxable income, slab tax, rebate, cess, / 12)
    for an employee in a given month using the live database rules.
    """
    canonical_month, _, p_start, p_end = _normalize_month_and_run_id(month)
    calc = calculate_employee_month_from_db(session, employee_id=employee_id, month=canonical_month)
    rules = load_tax_and_statutory_rules_from_db(session, p_start, p_end)

    breakdown = calculate_annual_tax_breakdown(
        monthly_fixed_gross=calc["monthly_fixed_gross"],
        payable_days=calc["payable_days"],
        calendar_days=calc["calendar_days"],
        variable_pay=calc["variable_pay"],
        overtime_pay=calc["overtime_pay"],
        standard_deduction=rules["standard_deduction"],
        rebate_threshold=rules["rebate_threshold"],
        cess_percent=rules["cess_percent"],
        slabs=rules["slabs"],
    )
    breakdown["employee_id"] = employee_id
    breakdown["month"] = canonical_month
    breakdown["financial_year"] = rules["financial_year"]
    breakdown["regime"] = rules["regime"]
    return breakdown


def change_slab_and_rerun_month(
    session: Session,
    slab_id: str = "TS-011",
    new_rate_percent: Decimal = Decimal("20.00"),
    month: str = "2026-09",
    employee_id: str = "EMP-0006",
    revert_after_demo: bool = True,
) -> dict[str, Any]:
    """Change a tax slab rate, rerun one payroll month, capture before/after tax for both the
    employee and the entire run, verify that past months are not altered, and optionally restore
    the slab and rerun back to baseline.
    """
    canonical_month, run_id, p_start, p_end = _normalize_month_and_run_id(month)
    slab = session.get(TaxSlab, slab_id.strip())
    if slab is None:
        raise NotFoundError(f"Tax slab '{slab_id}' not found.")

    emp = session.get(Employee, employee_id.strip())
    if emp is None:
        raise NotFoundError(f"Employee '{employee_id}' not found.")

    pr = session.get(PayrollRun, run_id)
    if pr is None:
        raise NotFoundError(f"Payroll run '{run_id}' not found.")

    # Pick a past payroll run from an earlier month to verify past months are never altered
    past_run = session.scalar(
        select(PayrollRun)
        .where(PayrollRun.run_id != run_id)
        .order_by(PayrollRun.period_start)
    )
    sample_past_run_id = past_run.run_id if past_run else "NONE"
    sample_past_tds_before = Decimal("0.00")
    if past_run:
        past_items = session.scalars(
            select(PayrollItem).where(PayrollItem.run_id == past_run.run_id)
        ).all()
        sample_past_tds_before = round_money(sum((to_dec(i.tds) for i in past_items), Decimal("0.00")))

    old_rate = round_money(slab.rate_percent)
    new_rate = round_money(new_rate_percent)

    # 1. Baseline (Before slab change)
    process_payroll_run(session, run_id=run_id, allow_rerun=True)
    before_emp_calc = calculate_employee_month_from_db(session, employee_id=emp.employee_id, month=canonical_month)
    before_emp_tax = get_employee_tax_breakdown(session, employee_id=emp.employee_id, month=canonical_month)

    items_before = session.scalars(select(PayrollItem).where(PayrollItem.run_id == run_id)).all()
    run_tds_before = round_money(sum((to_dec(i.tds) for i in items_before), Decimal("0.00")))
    run_net_before = round_money(pr.total_net)

    # 2. Apply slab change and rerun ONLY target month
    update_tax_slab(session, slab_id=slab.slab_id, rate_percent=new_rate)
    process_payroll_run(session, run_id=run_id, allow_rerun=True)
    session.refresh(pr)

    after_emp_calc = calculate_employee_month_from_db(session, employee_id=emp.employee_id, month=canonical_month)
    after_emp_tax = get_employee_tax_breakdown(session, employee_id=emp.employee_id, month=canonical_month)

    items_after = session.scalars(select(PayrollItem).where(PayrollItem.run_id == run_id)).all()
    run_tds_after = round_money(sum((to_dec(i.tds) for i in items_after), Decimal("0.00")))
    run_net_after = round_money(pr.total_net)

    # Verify past month was NOT altered
    sample_past_tds_after = Decimal("0.00")
    if past_run:
        past_items_after = session.scalars(
            select(PayrollItem).where(PayrollItem.run_id == past_run.run_id)
        ).all()
        sample_past_tds_after = round_money(sum((to_dec(i.tds) for i in past_items_after), Decimal("0.00")))

    past_untouched = sample_past_tds_before == sample_past_tds_after

    # 3. Revert slab back if requested
    if revert_after_demo:
        update_tax_slab(session, slab_id=slab.slab_id, rate_percent=old_rate)
        process_payroll_run(session, run_id=run_id, allow_rerun=True)

    return {
        "slab_id": slab.slab_id,
        "financial_year": slab.financial_year,
        "month_rerun": canonical_month,
        "run_id": run_id,
        "old_rate_percent": old_rate,
        "new_rate_percent": new_rate,
        "run_total_tds_before": run_tds_before,
        "run_total_tds_after": run_tds_after,
        "run_total_tds_difference": round_money(run_tds_after - run_tds_before),
        "run_total_net_before": run_net_before,
        "run_total_net_after": run_net_after,
        "past_months_untouched_verified": past_untouched,
        "sample_past_run_id": sample_past_run_id,
        "sample_past_run_tds_before": sample_past_tds_before,
        "sample_past_run_tds_after": sample_past_tds_after,
        "reverted_to_original": revert_after_demo,
        "employee_comparison": {
            "employee_id": emp.employee_id,
            "employee_name": emp.full_name,
            "month": canonical_month,
            "monthly_fixed_gross": before_emp_calc["monthly_fixed_gross"],
            "annual_taxable_income": before_emp_tax["annual_taxable_income"],
            "old_slab_rate_percent": old_rate,
            "new_slab_rate_percent": new_rate,
            "before_annual_tax": before_emp_tax["annual_total_tax"],
            "after_annual_tax": after_emp_tax["annual_total_tax"],
            "before_monthly_tds": before_emp_calc["tds"],
            "after_monthly_tds": after_emp_calc["tds"],
            "monthly_tds_difference": round_money(after_emp_calc["tds"] - before_emp_calc["tds"]),
            "before_net_pay": before_emp_calc["net_pay"],
            "after_net_pay": after_emp_calc["net_pay"],
        },
    }


# ==============================================================================
# 3. Monthly Statutory Reports: PF, ESI, TDS & 18-Month Reconciliation
# ==============================================================================


def get_monthly_pf_report(session: Session, month: str) -> dict[str, Any]:
    """Generate the monthly Provident Fund (PF) statutory report and reconcile totals against payroll_items."""
    canonical_month, run_id, p_start, p_end = _normalize_month_and_run_id(month)
    pr = session.get(PayrollRun, run_id)
    if pr is None:
        raise NotFoundError(f"Payroll run '{run_id}' not found.")

    rules = load_tax_and_statutory_rules_from_db(session, p_start, p_end)
    pf_ceiling = rules["pf_wage_ceiling"]

    items = list(
        session.scalars(
            select(PayrollItem)
            .where(PayrollItem.run_id == run_id)
            .order_by(PayrollItem.employee_id)
        ).all()
    )
    emp_map = {
        e.employee_id: e.full_name
        for e in session.scalars(select(Employee)).all()
    }

    rows: list[dict[str, Any]] = []
    tot_basic = Decimal("0.00")
    tot_pf_wage = Decimal("0.00")
    tot_pf_ee = Decimal("0.00")
    tot_pf_er = Decimal("0.00")

    for it in items:
        pf_ee = round_money(it.pf_employee)
        pf_er = round_money(it.pf_employer)
        if pf_ee > Decimal("0.00") or pf_er > Decimal("0.00"):
            earned_b = round_money(it.basic)
            pf_w = round_money(min(earned_b, pf_ceiling))
            tot_basic += earned_b
            tot_pf_wage += pf_w
            tot_pf_ee += pf_ee
            tot_pf_er += pf_er
            rows.append(
                {
                    "employee_id": it.employee_id,
                    "employee_name": emp_map.get(it.employee_id, it.employee_id),
                    "department_id": it.department_id,
                    "monthly_fixed_gross": round_money(it.monthly_fixed_gross),
                    "earned_basic": earned_b,
                    "pf_wage": pf_w,
                    "pf_employee": pf_ee,
                    "pf_employer": pf_er,
                    "total_pf": round_money(pf_ee + pf_er),
                }
            )

    payroll_pf_ee = round_money(sum((to_dec(i.pf_employee) for i in items), Decimal("0.00")))
    payroll_pf_er = round_money(sum((to_dec(i.pf_employer) for i in items), Decimal("0.00")))
    report_total = round_money(tot_pf_ee + tot_pf_er)
    payroll_total = round_money(payroll_pf_ee + payroll_pf_er)
    diff = round_money(report_total - payroll_total)

    return {
        "report_type": "PROVIDENT_FUND_MONTHLY",
        "month": canonical_month,
        "run_id": run_id,
        "pf_employee_rate_percent": round_money(rules["pf_ee_rate"]),
        "pf_employer_rate_percent": round_money(rules["pf_er_rate"]),
        "pf_wage_ceiling": round_money(pf_ceiling),
        "employees_covered": len(rows),
        "total_earned_basic": round_money(tot_basic),
        "total_pf_wage": round_money(tot_pf_wage),
        "total_pf_employee": round_money(tot_pf_ee),
        "total_pf_employer": round_money(tot_pf_er),
        "total_pf_contribution": report_total,
        "payroll_pf_employee_sum": payroll_pf_ee,
        "payroll_pf_employer_sum": payroll_pf_er,
        "difference": diff,
        "is_reconciled": diff == Decimal("0.00"),
        "rows": rows,
    }


def get_monthly_esi_report(session: Session, month: str) -> dict[str, Any]:
    """Generate the monthly Employees' State Insurance (ESI) statutory report and reconcile against payroll_items."""
    canonical_month, run_id, p_start, p_end = _normalize_month_and_run_id(month)
    pr = session.get(PayrollRun, run_id)
    if pr is None:
        raise NotFoundError(f"Payroll run '{run_id}' not found.")

    rules = load_tax_and_statutory_rules_from_db(session, p_start, p_end)

    items = list(
        session.scalars(
            select(PayrollItem)
            .where(PayrollItem.run_id == run_id)
            .order_by(PayrollItem.employee_id)
        ).all()
    )
    emp_map = {
        e.employee_id: e.full_name
        for e in session.scalars(select(Employee)).all()
    }

    rows: list[dict[str, Any]] = []
    tot_gross = Decimal("0.00")
    tot_esi_ee = Decimal("0.00")
    tot_esi_er = Decimal("0.00")

    for it in items:
        esi_ee = round_money(it.esi_employee)
        esi_er = round_money(it.esi_employer)
        if esi_ee > Decimal("0.00") or esi_er > Decimal("0.00"):
            g_pay = round_money(it.gross_pay)
            tot_gross += g_pay
            tot_esi_ee += esi_ee
            tot_esi_er += esi_er
            rows.append(
                {
                    "employee_id": it.employee_id,
                    "employee_name": emp_map.get(it.employee_id, it.employee_id),
                    "department_id": it.department_id,
                    "monthly_fixed_gross": round_money(it.monthly_fixed_gross),
                    "gross_pay": g_pay,
                    "esi_employee": esi_ee,
                    "esi_employer": esi_er,
                    "total_esi": round_money(esi_ee + esi_er),
                }
            )

    payroll_esi_ee = round_money(sum((to_dec(i.esi_employee) for i in items), Decimal("0.00")))
    payroll_esi_er = round_money(sum((to_dec(i.esi_employer) for i in items), Decimal("0.00")))
    report_total = round_money(tot_esi_ee + tot_esi_er)
    payroll_total = round_money(payroll_esi_ee + payroll_esi_er)
    diff = round_money(report_total - payroll_total)

    return {
        "report_type": "ESI_MONTHLY",
        "month": canonical_month,
        "run_id": run_id,
        "esi_employee_rate_percent": round_money(rules["esi_ee_rate"]),
        "esi_employer_rate_percent": round_money(rules["esi_er_rate"]),
        "esi_wage_limit": round_money(rules["esi_wage_limit"]),
        "employees_covered": len(rows),
        "total_gross_covered": round_money(tot_gross),
        "total_esi_employee": round_money(tot_esi_ee),
        "total_esi_employer": round_money(tot_esi_er),
        "total_esi_contribution": report_total,
        "payroll_esi_employee_sum": payroll_esi_ee,
        "payroll_esi_employer_sum": payroll_esi_er,
        "difference": diff,
        "is_reconciled": diff == Decimal("0.00"),
        "rows": rows,
    }


def get_monthly_tds_report(session: Session, month: str) -> dict[str, Any]:
    """Generate the monthly Income Tax (TDS) statutory report and reconcile totals against payroll_items."""
    canonical_month, run_id, p_start, p_end = _normalize_month_and_run_id(month)
    pr = session.get(PayrollRun, run_id)
    if pr is None:
        raise NotFoundError(f"Payroll run '{run_id}' not found.")

    rules = load_tax_and_statutory_rules_from_db(session, p_start, p_end)
    std_ded = rules["standard_deduction"]

    items = list(
        session.scalars(
            select(PayrollItem)
            .where(PayrollItem.run_id == run_id)
            .order_by(PayrollItem.employee_id)
        ).all()
    )
    emp_map = {
        e.employee_id: e.full_name
        for e in session.scalars(select(Employee)).all()
    }

    rows: list[dict[str, Any]] = []
    tot_gross = Decimal("0.00")
    tot_tds = Decimal("0.00")

    for it in items:
        tds_amt = round_money(it.tds)
        mfg = round_money(it.monthly_fixed_gross)
        g_pay = round_money(it.gross_pay)
        tot_gross += g_pay
        if tds_amt > Decimal("0.00"):
            ann_taxable = max(
                Decimal("0.00"),
                round_money((mfg * Decimal("12")) - std_ded + to_dec(it.variable_pay) + to_dec(it.overtime_pay)),
            )
            tot_tds += tds_amt
            rows.append(
                {
                    "employee_id": it.employee_id,
                    "employee_name": emp_map.get(it.employee_id, it.employee_id),
                    "department_id": it.department_id,
                    "monthly_fixed_gross": mfg,
                    "gross_pay": g_pay,
                    "annual_taxable_income": ann_taxable,
                    "tds": tds_amt,
                }
            )

    payroll_tds = round_money(sum((to_dec(i.tds) for i in items), Decimal("0.00")))
    diff = round_money(tot_tds - payroll_tds)

    return {
        "report_type": "TDS_MONTHLY",
        "month": canonical_month,
        "run_id": run_id,
        "financial_year": rules["financial_year"],
        "standard_deduction": round_money(std_ded),
        "rebate_threshold": round_money(rules["rebate_threshold"]),
        "cess_percent": round_money(rules["cess_percent"]),
        "employees_taxed": len(rows),
        "total_employees_in_run": len(items),
        "total_gross_pay": round_money(tot_gross),
        "total_tds": round_money(tot_tds),
        "payroll_tds_sum": payroll_tds,
        "difference": diff,
        "is_reconciled": diff == Decimal("0.00"),
        "rows": rows,
    }


def get_all_months_statutory_summary(session: Session) -> dict[str, Any]:
    """Reconcile PF, ESI, Professional Tax, and TDS report totals across all payroll runs against payroll_items."""
    runs = list(
        session.scalars(select(PayrollRun).order_by(PayrollRun.period_start, PayrollRun.run_id)).all()
    )
    month_rows: list[dict[str, Any]] = []
    max_diff = Decimal("0.00")
    all_ok = True

    g_pf_ee = Decimal("0.00")
    g_pf_er = Decimal("0.00")
    g_esi_ee = Decimal("0.00")
    g_esi_er = Decimal("0.00")
    g_pt = Decimal("0.00")
    g_tds = Decimal("0.00")

    for pr in runs:
        m_str = pr.period_start.strftime("%Y-%m")
        pf_rep = get_monthly_pf_report(session, m_str)
        esi_rep = get_monthly_esi_report(session, m_str)
        tds_rep = get_monthly_tds_report(session, m_str)

        items = list(
            session.scalars(select(PayrollItem).where(PayrollItem.run_id == pr.run_id)).all()
        )
        pt_sum = round_money(sum((to_dec(i.professional_tax) for i in items), Decimal("0.00")))

        rep_stat_total = round_money(
            pf_rep["total_pf_employee"]
            + pf_rep["total_pf_employer"]
            + esi_rep["total_esi_employee"]
            + esi_rep["total_esi_employer"]
            + pt_sum
            + tds_rep["total_tds"]
        )
        pay_stat_total = round_money(
            sum(
                (
                    to_dec(i.pf_employee)
                    + to_dec(i.pf_employer)
                    + to_dec(i.esi_employee)
                    + to_dec(i.esi_employer)
                    + to_dec(i.professional_tax)
                    + to_dec(i.tds)
                    for i in items
                ),
                Decimal("0.00"),
            )
        )
        diff = round_money(rep_stat_total - pay_stat_total)
        if abs(diff) > max_diff:
            max_diff = abs(diff)
        if diff != Decimal("0.00"):
            all_ok = False

        g_pf_ee += pf_rep["total_pf_employee"]
        g_pf_er += pf_rep["total_pf_employer"]
        g_esi_ee += esi_rep["total_esi_employee"]
        g_esi_er += esi_rep["total_esi_employer"]
        g_pt += pt_sum
        g_tds += tds_rep["total_tds"]

        month_rows.append(
            {
                "month": m_str,
                "run_id": pr.run_id,
                "employees_paid": pr.employees_paid,
                "pf_employee": pf_rep["total_pf_employee"],
                "pf_employer": pf_rep["total_pf_employer"],
                "esi_employee": esi_rep["total_esi_employee"],
                "esi_employer": esi_rep["total_esi_employer"],
                "professional_tax": pt_sum,
                "tds": tds_rep["total_tds"],
                "report_total_statutory": rep_stat_total,
                "payroll_total_statutory": pay_stat_total,
                "difference": diff,
                "is_reconciled": diff == Decimal("0.00"),
            }
        )

    return {
        "months_checked": len(month_rows),
        "all_reconciled": all_ok,
        "max_abs_difference": round_money(max_diff),
        "grand_total_pf_employee": round_money(g_pf_ee),
        "grand_total_pf_employer": round_money(g_pf_er),
        "grand_total_esi_employee": round_money(g_esi_ee),
        "grand_total_esi_employer": round_money(g_esi_er),
        "grand_total_professional_tax": round_money(g_pt),
        "grand_total_tds": round_money(g_tds),
        "months": month_rows,
    }
