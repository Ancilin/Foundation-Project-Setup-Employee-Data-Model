"""Build the small shared sample file (10 employees) from the master dataset.

Usage (from repo root):
    python scripts/make_sample_data.py path/to/01_LedgerForge_Python_Master_Dataset.xlsx

Writes docs/sample_employees.json and docs/sample_employees.csv. The dataset is
fictional (example domain `znova-demo.example`), so the sample is safe to share.
Requires `openpyxl` (see requirements-dev.txt).
"""

import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path

import openpyxl

# Fields the draft contract exposes. Post-outcome / sensitive-detail columns
# (exit_reason, career_gap_months, commute_distance_km, ...) are left out for now.
FIELDS = [
    "employee_id",
    "first_name",
    "last_name",
    "work_email",
    "gender",
    "date_of_birth",
    "hire_date",
    "exit_date",
    "employment_status",
    "employment_type",
    "department_id",
    "role_id",
    "manager_id",
    "work_location",
    "work_mode",
]

N_ACTIVE, N_LEFT = 8, 2
OUT_DIR = Path(__file__).resolve().parent.parent / "docs"


def _clean(value):
    if isinstance(value, (datetime, date)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    return value


def main(xlsx_path: str) -> None:
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    rows = wb["employees"].iter_rows(values_only=True)
    header = next(rows)
    active, left = [], []
    for row in rows:
        rec = dict(zip(header, row))
        bucket = active if rec["employment_status"] == "Active" else left
        if len(bucket) < (N_ACTIVE if bucket is active else N_LEFT):
            bucket.append({f: _clean(rec[f]) for f in FIELDS})
        if len(active) == N_ACTIVE and len(left) == N_LEFT:
            break

    sample = sorted(active + left, key=lambda r: r["employee_id"])
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "sample_employees.json").write_text(
        json.dumps(sample, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with (OUT_DIR / "sample_employees.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sample)
    print(f"Wrote {len(sample)} employees to {OUT_DIR}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
