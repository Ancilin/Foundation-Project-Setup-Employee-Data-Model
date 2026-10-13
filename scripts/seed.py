"""Master Dataset Seed Pipeline with Faker, Pandas, and CSV Exports.

Usage:
    python -m scripts.seed [--export] [--days 60] [--limit 100]

Arguments:
    --export    Also generate CSV files in exports/ directory (default: True)
    --days      Number of business days of attendance to generate (default: 60)
    --limit     Max employees to generate salaries & attendance for (default: None = all 745)
"""

import argparse
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from faker import Faker
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db.session import get_engine  # noqa: E402
from app.models import Attendance, Department, Employee, Role, Salary  # noqa: E402
from scripts.export_csv import export_all_to_csv  # noqa: E402

# Fixed seed for 100% reproducible synthetic generation
RANDOM_SEED = 42


def get_faker() -> Faker:
    fake = Faker("en_IN")
    Faker.seed(RANDOM_SEED)
    random.seed(RANDOM_SEED)
    return fake


def _to_date(val):
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def seed_master_dataset(
    xlsx_path: Path,
    attendance_days: int = 60,
    employee_limit: int | None = None,
    do_export: bool = True,
    session: Session | None = None,
) -> dict[str, int]:
    """Seed the database with departments, roles, faker-enhanced employees, salaries, and attendance.

    Idempotent: safely re-runnable without duplicate keys or data explosion.
    """
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {xlsx_path}")

    print(f"=== Starting Seed Pipeline (Seed: {RANDOM_SEED}) ===")
    print(f"Reading dataset: {xlsx_path.name}...")

    fake = get_faker()
    counts = {"departments": 0, "roles": 0, "employees": 0, "salaries": 0, "attendance": 0}

    def _run_seed(session: Session):
        # -------------------------------------------------------------
        # 1. Departments
        # -------------------------------------------------------------
        df_depts = pd.read_excel(xlsx_path, sheet_name="departments")
        existing_depts = set(session.scalars(select(Department.department_id)).all())
        new_depts = 0

        for _, row in df_depts.iterrows():
            did = str(row["department_id"]).strip()
            if did in existing_depts:
                continue
            dept = Department(
                department_id=did,
                department_name=str(row["department_name"]).strip(),
                cost_center=str(row["cost_center"]).strip(),
                description=str(row["description"]).strip() if pd.notna(row.get("description")) else None,
            )
            session.add(dept)
            existing_depts.add(did)
            new_depts += 1

        session.commit()
        counts["departments"] = len(existing_depts)
        print(f"[Departments] {new_depts} inserted, total in DB: {len(existing_depts)}")

        # -------------------------------------------------------------
        # 2. Roles
        # -------------------------------------------------------------
        df_roles = pd.read_excel(xlsx_path, sheet_name="roles")
        existing_roles = set(session.scalars(select(Role.role_id)).all())
        new_roles = 0
        roles_lookup: dict[str, Role] = {}

        for _, row in df_roles.iterrows():
            rid = str(row["role_id"]).strip()
            if rid not in existing_roles:
                role = Role(
                    role_id=rid,
                    department_id=str(row["department_id"]).strip(),
                    role_title=str(row["role_title"]).strip(),
                    level=int(row["level"]),
                    grade=str(row["grade"]).strip(),
                    band_min_annual=float(row["band_min_annual"]),
                    band_mid_annual=float(row["band_mid_annual"]),
                    band_max_annual=float(row["band_max_annual"]),
                    overtime_eligible=(str(row.get("overtime_eligible", "")).upper() == "Y"),
                )
                session.add(role)
                existing_roles.add(rid)
                new_roles += 1

        session.commit()
        counts["roles"] = len(existing_roles)
        print(f"[Roles] {new_roles} inserted, total in DB: {len(existing_roles)}")

        # Build roles lookup for salary band generation
        for r in session.scalars(select(Role)).all():
            roles_lookup[r.role_id] = r

        # -------------------------------------------------------------
        # 3. Employees (Realistic, No 'test123' style data)
        # -------------------------------------------------------------
        df_emps = pd.read_excel(xlsx_path, sheet_name="employees")
        if employee_limit:
            df_emps = df_emps.head(employee_limit)

        existing_emps = set(session.scalars(select(Employee.employee_id)).all())
        new_emps = 0

        # Deterministic generation using Faker
        for idx, row in df_emps.iterrows():
            eid = str(row["employee_id"]).strip()
            if eid in existing_emps:
                continue

            gender = str(row["gender"]).strip() if pd.notna(row.get("gender")) else "Other"
            if gender == "Male":
                first_name = fake.first_name_male()
            elif gender == "Female":
                first_name = fake.first_name_female()
            else:
                first_name = fake.first_name()
            last_name = fake.last_name()

            # Clean professional corporate email format
            clean_first = "".join(c for c in first_name.lower() if c.isalnum())
            clean_last = "".join(c for c in last_name.lower() if c.isalnum())
            work_email = f"{clean_first}.{clean_last}.{eid.lower().replace('-', '')}@znova-demo.example"

            emp = Employee(
                employee_id=eid,
                first_name=first_name,
                last_name=last_name,
                work_email=work_email,
                gender=gender,
                date_of_birth=_to_date(row["date_of_birth"]),
                hire_date=_to_date(row["hire_date"]),
                exit_date=_to_date(row.get("exit_date")),
                employment_status=str(row["employment_status"]).strip(),
                employment_type=str(row["employment_type"]).strip(),
                department_id=str(row["department_id"]).strip(),
                role_id=str(row["role_id"]).strip(),
                manager_id=None,  # Assigned in pass 2 once all employees exist
                work_location=str(row["work_location"]).strip(),
                work_mode=str(row["work_mode"]).strip(),
            )
            session.add(emp)
            existing_emps.add(eid)
            new_emps += 1

        session.commit()

        # Pass 2: Connect manager_id hierarchy safely
        for _, row in df_emps.iterrows():
            eid = str(row["employee_id"]).strip()
            raw_mgr = row.get("manager_id")
            if pd.notna(raw_mgr):
                mgr_id = str(raw_mgr).strip()
                if mgr_id in existing_emps and mgr_id != eid:
                    emp_record = session.get(Employee, eid)
                    if emp_record and emp_record.manager_id != mgr_id:
                        emp_record.manager_id = mgr_id

        session.commit()
        counts["employees"] = len(existing_emps)
        print(f"[Employees] {new_emps} inserted, total in DB: {len(existing_emps)}")

        # -------------------------------------------------------------
        # 4. Salaries (Linked to employee & aligned with role band)
        # -------------------------------------------------------------
        existing_salaries = set(session.scalars(select(Salary.employee_id)).all())
        new_salaries = 0

        employees = session.scalars(select(Employee)).all()
        for emp in employees:
            if emp.employee_id in existing_salaries:
                continue

            role = roles_lookup.get(emp.role_id)
            min_band = float(role.band_min_annual) if role else 500000.0
            max_band = float(role.band_max_annual) if role else 1000000.0

            # Deterministic salary based on employee ID hash
            emp_rng = random.Random(emp.employee_id)
            annual_ctc = round(emp_rng.uniform(min_band, max_band), 2)
            monthly_gross = round(annual_ctc / 12.0, 2)
            basic = round(monthly_gross * 0.50, 2)
            hra = round(basic * 0.50, 2)
            special_allowance = round(monthly_gross - basic - hra, 2)

            sal = Salary(
                salary_id=f"SAL-{emp.employee_id}",
                employee_id=emp.employee_id,
                monthly_gross=monthly_gross,
                basic=basic,
                hra=hra,
                special_allowance=special_allowance,
                annual_ctc=annual_ctc,
                effective_from=emp.hire_date,
                effective_to=emp.exit_date,
            )
            session.add(sal)
            existing_salaries.add(emp.employee_id)
            new_salaries += 1

        session.commit()
        counts["salaries"] = len(existing_salaries)
        print(f"[Salaries] {new_salaries} inserted, total in DB: {len(existing_salaries)}")

        # -------------------------------------------------------------
        # 5. Attendance (Linked by employee_id over recent business days)
        # -------------------------------------------------------------
        existing_att_keys = set(
            session.execute(select(Attendance.employee_id, Attendance.attendance_date)).all()
        )
        new_attendance = 0

        # Generate business days going backwards from a fixed reference date
        ref_date = date(2026, 9, 30)  # matching dataset cutoff
        business_days: list[date] = []
        curr = ref_date
        while len(business_days) < attendance_days:
            if curr.weekday() < 5:  # Monday to Friday
                business_days.append(curr)
            curr -= timedelta(days=1)
        business_days.reverse()

        # Generate for active or eligible employees
        # Use a batch of employees to keep generation fast and comprehensive
        sample_employees = [e for e in employees if e.employment_status == "Active"][:150]

        att_objects: list[Attendance] = []
        for emp in sample_employees:
            emp_rng = random.Random(f"{emp.employee_id}-attendance")
            for bday in business_days:
                if bday < emp.hire_date or (emp.exit_date and bday > emp.exit_date):
                    continue
                if (emp.employee_id, bday) in existing_att_keys:
                    continue

                # Realistic status distribution
                p = emp_rng.random()
                if p < 0.78:
                    status = "PRESENT"
                    in_min = emp_rng.randint(45, 75)
                    check_in = f"09:{in_min:02d}" if in_min < 60 else f"10:{in_min-60:02d}"
                    check_out = "18:15"
                    hours = round(emp_rng.uniform(7.8, 9.2), 2)
                    late = "Y" if in_min >= 60 else "N"
                    ot = round(max(0.0, hours - 8.0), 2)
                elif p < 0.90:
                    status = "WFH"
                    check_in = "09:00"
                    check_out = "18:00"
                    hours = 8.00
                    late = "N"
                    ot = 0.0
                elif p < 0.95:
                    status = "ON_LEAVE"
                    check_in, check_out, hours, late, ot = None, None, 0.0, "N", 0.0
                elif p < 0.98:
                    status = "HALF_DAY"
                    check_in, check_out, hours, late, ot = "09:15", "13:30", 4.0, "N", 0.0
                else:
                    status = "ABSENT"
                    check_in, check_out, hours, late, ot = None, None, 0.0, "N", 0.0

                weekday_str = bday.strftime("%a")
                att_id = f"ATT-{emp.employee_id}-{bday.strftime('%Y%m%d')}"

                att = Attendance(
                    attendance_id=att_id,
                    employee_id=emp.employee_id,
                    attendance_date=bday,
                    weekday=weekday_str,
                    status=status,
                    check_in=check_in,
                    check_out=check_out,
                    hours_worked=hours,
                    overtime_hours=ot,
                    late_flag=late,
                )
                att_objects.append(att)
                existing_att_keys.add((emp.employee_id, bday))
                new_attendance += 1

                if len(att_objects) >= 500:
                    session.add_all(att_objects)
                    session.commit()
                    att_objects.clear()

        if att_objects:
            session.add_all(att_objects)
            session.commit()

        total_att = session.scalar(select(func.count(Attendance.attendance_id))) or len(existing_att_keys)
        counts["attendance"] = total_att
        print(f"[Attendance] {new_attendance} inserted, total in DB: {total_att}")

    if session is not None:
        _run_seed(session)
    else:
        with Session(get_engine()) as s:
            _run_seed(s)

    # -------------------------------------------------------------
    # 6. CSV Exports
    # -------------------------------------------------------------
    if do_export:
        print("\n=== Generating CSV Exports ===")
        export_counts = export_all_to_csv(session=session)
        print(f"Exported tables: {export_counts}")

    print("\n=== Seeding Finished Successfully ===")
    return counts


def main():
    parser = argparse.ArgumentParser(description="Seed LedgerForge database with master dataset")
    parser.add_argument(
        "--file",
        type=Path,
        default=ROOT / "01_LedgerForge_Python_Master_Dataset.xlsx",
        help="Path to Excel dataset",
    )
    parser.add_argument("--days", type=int, default=60, help="Days of attendance")
    parser.add_argument("--limit", type=int, default=None, help="Employee limit for speed (optional)")
    parser.add_argument("--no-export", action="store_true", help="Skip CSV export")

    args = parser.parse_args()
    seed_master_dataset(
        xlsx_path=args.file,
        attendance_days=args.days,
        employee_limit=args.limit,
        do_export=not args.no_export,
    )


if __name__ == "__main__":
    main()
