"""Generate 3 sample payslip PDFs and compare their engine figures against payroll_items.csv (LF-08)."""

from decimal import Decimal
from pathlib import Path
import sys

import pandas as pd
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db.session import get_engine  # noqa: E402
from app.services.payslip_service import format_inr, generate_payslip_pdf, get_payslip_data  # noqa: E402

SAMPLE_TARGETS = [
    ("EMP-0002", "PR-2025-04"),  # High earner with Variable Pay (Performance Bonus) & TDS
    ("EMP-0011", "PR-2025-04"),  # LOP (0.5 days), Overtime (1.5 hrs), Variable Pay, PF
    ("EMP-0049", "PR-2025-04"),  # Low fixed gross (18,000 <= 21,000) with ESI (0.75% / 3.25%), Overtime (10.5 hrs), LOP (1.5 days)
]


def main() -> None:
    engine = get_engine()
    csv_path = ROOT / "data" / "csv" / "payroll_items.csv"
    df_pi = pd.read_csv(csv_path)
    out_dir = ROOT / "exports" / "payslips"
    out_dir.mkdir(parents=True, exist_ok=True)

    fields_to_compare = [
        "monthly_fixed_gross",
        "basic",
        "hra",
        "conveyance",
        "medical",
        "special_allowance",
        "earned_fixed_pay",
        "overtime_pay",
        "variable_pay",
        "gross_pay",
        "pf_employee",
        "esi_employee",
        "professional_tax",
        "tds",
        "other_deductions",
        "total_deductions",
        "net_pay",
    ]

    with Session(engine) as session:
        for emp_id, run_id in SAMPLE_TARGETS:
            payslip = get_payslip_data(
                session=session,
                employee_id=emp_id,
                run_id=run_id,
                requester_id=emp_id,
                requester_role="EMPLOYEE",
            )
            pdf_path = out_dir / f"payslip_{emp_id}_{run_id}.pdf"
            pdf_bytes = generate_payslip_pdf(payslip, output_path=pdf_path)

            csv_row = df_pi[(df_pi["employee_id"] == emp_id) & (df_pi["run_id"] == run_id)].iloc[0]

            print("=" * 88)
            print(f"PAYSLIP COMPARISON: {emp_id} ({payslip['employee_name']}) | Run: {run_id}")
            print(f"PDF Saved: {pdf_path} ({len(pdf_bytes):,} bytes)")
            print(f"Net Pay (Indian Format): INR {payslip['net_pay_formatted']} ({payslip['net_pay_in_words']})")
            print("-" * 88)
            print(f"{'Component / Field':<24} | {'payroll_items.csv':>16} | {'Engine Payslip':>16} | {'Indian Format':>16} | {'Match'}")
            print("-" * 88)

            all_match = True
            for field in fields_to_compare:
                csv_val = Decimal(str(csv_row[field])).quantize(Decimal("0.01"))
                eng_val = Decimal(str(payslip[field])).quantize(Decimal("0.01"))
                fmt_val = payslip.get(f"{field}_formatted", format_inr(eng_val))
                matched = csv_val == eng_val
                if not matched:
                    all_match = False
                status = "EXACT" if matched else "DIFF"
                print(f"{field:<24} | {str(csv_val):>16} | {str(eng_val):>16} | {fmt_val:>16} | {status}")

            print("-" * 88)
            assert all_match, f"Mismatch found for {emp_id} in {run_id}!"
            print(f"RESULT: 100% EXACT MATCH across all {len(fields_to_compare)} payslip figures for {emp_id}\n")


if __name__ == "__main__":
    main()
