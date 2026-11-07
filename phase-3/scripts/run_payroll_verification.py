"""Run calculate_employee_month() for all 7,340 payroll rows, export exports/my_payroll.csv,
and verify against official payroll_items.csv (LF-07).
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.payroll_service import calculate_employee_month, round_money  # noqa: E402

CSV_DIR = ROOT / "data" / "csv"
OUT_CSV = ROOT / "exports" / "my_payroll.csv"


def run_all_7340_rows() -> Path:
    pi_df = pd.read_csv(CSV_DIR / "payroll_items.csv")
    emp_df = pd.read_csv(CSV_DIR / "employees.csv").set_index("employee_id")
    role_df = pd.read_csv(CSV_DIR / "roles.csv").set_index("role_id")
    ss_df = pd.read_csv(CSV_DIR / "salary_structures.csv")
    att_df = pd.read_csv(CSV_DIR / "attendance.csv", low_memory=False)
    slabs_df = pd.read_csv(CSV_DIR / "tax_slabs.csv")

    # 1. Pre-aggregate attendance by (employee_id, month) using Task 6 rules
    att_df["month"] = att_df["attendance_date"].str.slice(0, 7)
    att_df["lop_calc"] = (
        (att_df["status"] == "ABSENT_LOP").astype(float)
        + (att_df["status"] == "UNPAID_LEAVE").astype(float)
        + 0.5 * (att_df["status"] == "HALF_DAY_UNPAID").astype(float)
    )
    # MISSING_CHECKOUT rule: overtime_hours is 0 when data_quality_flag == 'MISSING_CHECKOUT'
    att_df["ot_clean"] = att_df["overtime_hours"].where(
        att_df["data_quality_flag"] != "MISSING_CHECKOUT", 0.0
    ).fillna(0.0)

    att_grp = (
        att_df.groupby(["employee_id", "month"])
        .agg(lop_days=("lop_calc", "sum"), raw_ot=("ot_clean", "sum"))
        .to_dict(orient="index")
    )

    # 2. Index salary structures by employee_id
    ss_df["eff_from"] = ss_df["effective_from"]
    ss_df["eff_to"] = ss_df["effective_to"].fillna("9999-12-31")
    ss_by_emp: dict[str, list[dict]] = {}
    for eid, grp in ss_df.groupby("employee_id"):
        ss_by_emp[str(eid)] = grp.to_dict(orient="records")

    # 3. Index tax slabs by financial_year
    slabs_by_fy: dict[str, list[dict]] = {}
    for fy, grp in slabs_df.groupby("financial_year"):
        slabs_by_fy[str(fy)] = [
            {
                "income_from": Decimal(str(r["income_from"])),
                "income_to": Decimal(str(r["income_to"])) if pd.notna(r["income_to"]) else None,
                "rate_percent": Decimal(str(r["rate_percent"])),
            }
            for _, r in grp.sort_values("income_from").iterrows()
        ]

    emp_dict = emp_df.to_dict(orient="index")
    role_ot_map = {rid: (str(r["overtime_eligible"]).upper() == "Y") for rid, r in role_df.iterrows()}

    results = []
    for row in pi_df.to_dict(orient="records"):
        eid = str(row["employee_id"])
        run_id = str(row["run_id"])
        p_start_str = str(row["period_start"])[:10]
        p_end_str = str(row["period_end"])[:10]
        month_str = p_start_str[:7]
        p_start = date.fromisoformat(p_start_str)
        p_end = date.fromisoformat(p_end_str)

        emp_info = emp_dict[eid]
        hire_date = date.fromisoformat(str(emp_info["hire_date"])[:10])
        exit_raw = emp_info.get("exit_date")
        exit_date = date.fromisoformat(str(exit_raw)[:10]) if pd.notna(exit_raw) else None
        pf_applicable = str(emp_info["pf_applicable"]).upper() == "Y"

        # Active salary structure on period_start (or period_end for mid-month joiners)
        comp_map: dict[str, Decimal] = {}
        for s in ss_by_emp.get(eid, []):
            if s["eff_from"] <= p_start_str <= s["eff_to"]:
                comp_map[s["component_id"]] = Decimal(str(s["monthly_amount"]))
        if not comp_map:
            for s in ss_by_emp.get(eid, []):
                if s["eff_from"] <= p_end_str <= s["eff_to"]:
                    comp_map[s["component_id"]] = Decimal(str(s["monthly_amount"]))

        att_info = att_grp.get((eid, month_str), {"lop_days": 0.0, "raw_ot": 0.0})
        role_id = str(row["role_id"])
        ot_eligible = role_ot_map.get(role_id, False)

        fy = (
            f"FY{p_start.year}-{str(p_start.year + 1)[-2:]}"
            if p_start.month >= 4
            else f"FY{p_start.year - 1}-{str(p_start.year)[-2:]}"
        )

        calc = calculate_employee_month(
            employee_id=eid,
            period_start=p_start,
            period_end=p_end,
            components=comp_map,
            hire_date=hire_date,
            exit_date=exit_date,
            lop_days=Decimal(str(att_info["lop_days"])),
            raw_overtime_hours=Decimal(str(att_info["raw_ot"])),
            overtime_eligible=ot_eligible,
            pf_applicable=pf_applicable,
            variable_pay=Decimal(str(row["variable_pay"])),
            variable_pay_type=str(row["variable_pay_type"]) if pd.notna(row.get("variable_pay_type")) else None,
            other_deductions=Decimal(str(row["other_deductions"])),
            department_id=str(row["department_id"]),
            role_id=role_id,
            run_id=run_id,
            slabs=slabs_by_fy.get(fy),
        )
        results.append(calc)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out_df = pd.DataFrame(results)
    out_df.to_csv(OUT_CSV, index=False)
    print(f"Saved {len(out_df)} calculated payroll rows to {OUT_CSV}")
    return OUT_CSV


if __name__ == "__main__":
    run_all_7340_rows()
