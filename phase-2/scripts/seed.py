"""Master Dataset Seed Pipeline with Chunked Attendance & Leave Tables (LF-03, LF-05, LF-06).

Usage:
    python -m scripts.seed [--export] [--days 60] [--limit 100] [--reset]
"""

import argparse
import random
import sys
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from faker import Faker
import pandas as pd
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db.session import get_engine  # noqa: E402
from app.models import (  # noqa: E402
    Attendance,
    Base,
    ChartOfAccount,
    Client,
    Department,
    Employee,
    EmployeeAssignment,
    Holiday,
    Invoice,
    InvoiceItem,
    InvoicePayment,
    JournalEntry,
    JournalLine,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    PayrollItem,
    PayrollRun,
    Role,
    Salary,
    SalaryComponent,
    SalaryRevision,
    SalaryStructure,
    StatutoryRate,
    TaxParameter,
    TaxSlab,
)
from app.services.ledger_service import post_payroll_run_to_ledger  # noqa: E402
from scripts.export_csv import export_all_to_csv  # noqa: E402

RANDOM_SEED = 42


def get_faker() -> Faker:
    fake = Faker("en_IN")
    Faker.seed(RANDOM_SEED)
    random.seed(RANDOM_SEED)
    return fake


def _to_date(val) -> date | None:
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    try:
        return date.fromisoformat(s[:10])
    except Exception:
        return None


def _clean_str(val) -> str | None:
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    return s if s and s.lower() != "nan" else None


def load_attendance_in_chunks(
    session: Session,
    csv_path: Path,
    chunk_size: int = 10000,
    valid_emps: set[str] | None = None,
) -> int:
    """Load 150,000+ attendance rows efficiently in chunks using vectorized filtering and bulk insert."""
    existing_ids = set(session.scalars(select(Attendance.attendance_id)).all())
    if valid_emps is None:
        valid_emps = set(session.scalars(select(Employee.employee_id)).all())

    inserted_total = 0
    for df_chunk in pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False):
        df_chunk = df_chunk[df_chunk["employee_id"].isin(valid_emps)]
        if existing_ids:
            df_chunk = df_chunk[~df_chunk["attendance_id"].isin(existing_ids)]
        if df_chunk.empty:
            continue

        df_chunk = df_chunk.copy()
        df_chunk["attendance_date"] = pd.to_datetime(df_chunk["attendance_date"]).dt.date
        df_chunk["overtime_hours"] = df_chunk["overtime_hours"].fillna(0.0)
        df_chunk["late_flag"] = df_chunk["late_flag"].fillna("N")

        # Replace NaN with None for nullable columns
        df_chunk = df_chunk.where(pd.notna(df_chunk), None)

        records = df_chunk[
            [
                "attendance_id",
                "employee_id",
                "attendance_date",
                "weekday",
                "status",
                "leave_type_code",
                "check_in",
                "check_out",
                "hours_worked",
                "overtime_hours",
                "late_flag",
                "source",
                "data_quality_flag",
                "department_id",
            ]
        ].to_dict(orient="records")

        if records:
            session.execute(insert(Attendance), records)
            session.commit()
            existing_ids.update(r["attendance_id"] for r in records)
            inserted_total += len(records)

    return inserted_total


def seed_master_dataset(
    xlsx_path: Path,
    attendance_days: int = 60,
    employee_limit: int | None = None,
    do_export: bool = True,
    session: Session | None = None,
    chunk_size: int = 10000,
) -> dict[str, int]:
    """Seed the database with all reference, employee, salary, attendance, and leave tables."""
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {xlsx_path}")

    t0 = time.perf_counter()
    print(f"=== Starting Seed Pipeline (Seed: {RANDOM_SEED}) ===")
    print(f"Reading dataset: {xlsx_path.name}...")

    fake = get_faker()
    counts: dict[str, int] = {
        "departments": 0,
        "roles": 0,
        "employees": 0,
        "salaries": 0,
        "attendance": 0,
        "holidays": 0,
        "leave_types": 0,
        "leave_balances": 0,
        "leave_requests": 0,
    }

    csv_dir = ROOT / "data" / "csv"

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

        for r in session.scalars(select(Role)).all():
            roles_lookup[r.role_id] = r

        # -------------------------------------------------------------
        # 3. Employees
        # -------------------------------------------------------------
        df_emps = pd.read_excel(xlsx_path, sheet_name="employees")
        if employee_limit:
            df_emps = df_emps.head(employee_limit)

        existing_emps = set(session.scalars(select(Employee.employee_id)).all())
        new_emps = 0

        for _, row in df_emps.iterrows():
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
                manager_id=None,
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
        # 4. Salaries
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
        # 5. Holidays & Leave Types (LF-06)
        # -------------------------------------------------------------
        csv_hol_path = csv_dir / "holidays.csv"
        if csv_hol_path.exists():
            df_hol = pd.read_csv(csv_hol_path)
            existing_hol = set(session.scalars(select(Holiday.holiday_date)).all())
            new_hol = 0
            for _, row in df_hol.iterrows():
                hdate = _to_date(row["holiday_date"])
                if hdate and hdate not in existing_hol:
                    session.add(
                        Holiday(
                            holiday_date=hdate,
                            holiday_name=str(row["holiday_name"]).strip(),
                            holiday_type=str(row["holiday_type"]).strip(),
                            weekday=str(row["weekday"]).strip(),
                            falls_on_weekend=str(row["falls_on_weekend"]).strip(),
                            calendar_note=_clean_str(row.get("calendar_note")),
                        )
                    )
                    existing_hol.add(hdate)
                    new_hol += 1
            session.commit()
            counts["holidays"] = len(existing_hol)
            print(f"[Holidays] {new_hol} inserted, total in DB: {len(existing_hol)}")

        csv_lt_path = csv_dir / "leave_types.csv"
        if csv_lt_path.exists():
            df_lt = pd.read_csv(csv_lt_path)
            existing_lt = set(session.scalars(select(LeaveType.leave_type_code)).all())
            new_lt = 0
            for _, row in df_lt.iterrows():
                code = str(row["leave_type_code"]).strip()
                if code not in existing_lt:
                    session.add(
                        LeaveType(
                            leave_type_code=code,
                            leave_type_name=str(row["leave_type_name"]).strip(),
                            pay_type=str(row["pay_type"]).strip(),
                            annual_quota_days=int(row["annual_quota_days"]),
                            prorated_for_joiners=str(row["prorated_for_joiners"]).strip(),
                            carry_forward_allowed=str(row["carry_forward_allowed"]).strip(),
                            max_carry_forward_days=int(row["max_carry_forward_days"]),
                            policy_note=_clean_str(row.get("policy_note")),
                        )
                    )
                    existing_lt.add(code)
                    new_lt += 1
            session.commit()
            counts["leave_types"] = len(existing_lt)
            print(f"[Leave Types] {new_lt} inserted, total in DB: {len(existing_lt)}")

        # -------------------------------------------------------------
        # 6. Leave Balances & Leave Requests (LF-06)
        # -------------------------------------------------------------
        csv_lb_path = csv_dir / "leave_balances.csv"
        if csv_lb_path.exists():
            df_lb = pd.read_csv(csv_lb_path)
            existing_lb = set(session.scalars(select(LeaveBalance.employee_id)).all())
            new_lb = 0
            lb_records = []
            for row in df_lb.to_dict(orient="records"):
                eid = str(row["employee_id"]).strip()
                if eid not in existing_lb and eid in existing_emps:
                    lb_records.append(
                        {
                            "employee_id": eid,
                            "as_of_date": _to_date(row["as_of_date"]),
                            "financial_year": str(row["financial_year"]).strip(),
                            "cl_entitlement": Decimal(str(row["cl_entitlement"])),
                            "cl_used": Decimal(str(row["cl_used"])),
                            "cl_balance": Decimal(str(row["cl_balance"])),
                            "sl_entitlement": Decimal(str(row["sl_entitlement"])),
                            "sl_used": Decimal(str(row["sl_used"])),
                            "sl_balance": Decimal(str(row["sl_balance"])),
                            "el_used_fy": Decimal(str(row["el_used_fy"])),
                            "el_balance": Decimal(str(row["el_balance"])),
                            "pending_days": Decimal(str(row["pending_days"])),
                        }
                    )
                    existing_lb.add(eid)
                    new_lb += 1
            if lb_records:
                session.execute(insert(LeaveBalance), lb_records)
                session.commit()
            counts["leave_balances"] = len(existing_lb)
            print(f"[Leave Balances] {new_lb} inserted, total in DB: {len(existing_lb)}")

        csv_lr_path = csv_dir / "leave_requests.csv"
        if csv_lr_path.exists():
            df_lr = pd.read_csv(csv_lr_path)
            existing_lr = set(session.scalars(select(LeaveRequest.leave_request_id)).all())
            new_lr = 0
            lr_records = []
            for row in df_lr.to_dict(orient="records"):
                lrid = str(row["leave_request_id"]).strip()
                eid = str(row["employee_id"]).strip()
                approver = _clean_str(row.get("approver_id"))
                if approver and approver not in existing_emps:
                    approver = None
                if lrid not in existing_lr and eid in existing_emps:
                    lr_records.append(
                        {
                            "leave_request_id": lrid,
                            "employee_id": eid,
                            "leave_type_code": str(row["leave_type_code"]).strip(),
                            "start_date": _to_date(row["start_date"]),
                            "end_date": _to_date(row["end_date"]),
                            "days": Decimal(str(row["days"])),
                            "reason": _clean_str(row.get("reason")),
                            "status": str(row["status"]).strip(),
                            "applied_on": _to_date(row["applied_on"]),
                            "approver_id": approver,
                            "decided_on": _to_date(row.get("decided_on")),
                        }
                    )
                    existing_lr.add(lrid)
                    new_lr += 1
            if lr_records:
                session.execute(insert(LeaveRequest), lr_records)
                session.commit()
            counts["leave_requests"] = len(existing_lr)
            print(f"[Leave Requests] {new_lr} inserted, total in DB: {len(existing_lr)}")

        # -------------------------------------------------------------
        # 7. Attendance (Chunked CSV loader for full dataset, or fast subset for unit tests)
        # -------------------------------------------------------------
        csv_att_path = csv_dir / "attendance.csv"
        if employee_limit is None and csv_att_path.exists():
            new_attendance = load_attendance_in_chunks(
                session=session,
                csv_path=csv_att_path,
                chunk_size=chunk_size,
                valid_emps=existing_emps,
            )
            total_att = session.scalar(select(func.count(Attendance.attendance_id))) or 0
            counts["attendance"] = total_att
            print(f"[Attendance] {new_attendance} inserted in chunks of {chunk_size}, total in DB: {total_att}")
        else:
            existing_att_keys = set(
                session.execute(select(Attendance.employee_id, Attendance.attendance_date)).all()
            )
            new_attendance = 0
            ref_date = date(2026, 9, 30)
            business_days: list[date] = []
            curr = ref_date
            while len(business_days) < attendance_days:
                if curr.weekday() < 5:
                    business_days.append(curr)
                curr -= timedelta(days=1)
            business_days.reverse()

            sample_employees = [e for e in employees if e.employment_status == "Active"][:150]
            att_objects: list[Attendance] = []
            for emp in sample_employees:
                emp_rng = random.Random(f"{emp.employee_id}-attendance")
                for bday in business_days:
                    if bday < emp.hire_date or (emp.exit_date and bday > emp.exit_date):
                        continue
                    if (emp.employee_id, bday) in existing_att_keys:
                        continue

                    p = emp_rng.random()
                    if p < 0.78:
                        status = "PRESENT"
                        in_min = emp_rng.randint(45, 75)
                        check_in = f"09:{in_min:02d}" if in_min < 60 else f"10:{in_min-60:02d}"
                        check_out = "18:15"
                        hours = Decimal(str(round(emp_rng.uniform(7.8, 9.2), 2)))
                        late = "Y" if in_min >= 60 else "N"
                        ot = Decimal(str(round(max(0.0, float(hours) - 8.0), 2)))
                    elif p < 0.90:
                        status = "WFH"
                        check_in = "09:00"
                        check_out = "18:00"
                        hours = Decimal("8.00")
                        late = "N"
                        ot = Decimal("0.00")
                    elif p < 0.95:
                        status = "PAID_LEAVE"
                        check_in, check_out, hours, late, ot = None, None, Decimal("0.00"), "N", Decimal("0.00")
                    elif p < 0.98:
                        status = "HALF_DAY_UNPAID"
                        check_in, check_out, hours, late, ot = "09:15", "13:30", Decimal("4.00"), "N", Decimal("0.00")
                    else:
                        status = "ABSENT_LOP"
                        check_in, check_out, hours, late, ot = None, None, Decimal("0.00"), "N", Decimal("0.00")

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
                        department_id=emp.department_id,
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

        # -------------------------------------------------------------
        # 8. Employee Assignments (LF-02)
        # -------------------------------------------------------------
        csv_as_path = csv_dir / "employee_assignments.csv"
        if csv_as_path.exists():
            df_as = pd.read_csv(csv_as_path)
            existing_as = set(session.scalars(select(EmployeeAssignment.assignment_id)).all())
            new_as = 0
            as_records = []
            for row in df_as.to_dict(orient="records"):
                aid = str(row["assignment_id"]).strip()
                eid = str(row["employee_id"]).strip()
                if aid not in existing_as and eid in existing_emps:
                    as_records.append(
                        {
                            "assignment_id": aid,
                            "employee_id": eid,
                            "effective_from": _to_date(row["effective_from"]),
                            "effective_to": _to_date(row.get("effective_to")),
                            "department_id": str(row["department_id"]).strip(),
                            "role_id": str(row["role_id"]).strip(),
                            "job_level": _clean_str(row.get("job_level")),
                            "manager_id": _clean_str(row.get("manager_id")),
                            "change_reason": _clean_str(row.get("change_reason")),
                        }
                    )
                    existing_as.add(aid)
                    new_as += 1
            if as_records:
                session.execute(insert(EmployeeAssignment), as_records)
                session.commit()
            counts["employee_assignments"] = len(existing_as)
            print(f"[Employee Assignments] {new_as} inserted, total in DB: {len(existing_as)}")

        # -------------------------------------------------------------
        # 9. Salary Components (LF-05)
        # -------------------------------------------------------------
        csv_comp_path = csv_dir / "salary_components.csv"
        if csv_comp_path.exists():
            df_comp = pd.read_csv(csv_comp_path)
            existing_comp = set(session.scalars(select(SalaryComponent.component_id)).all())
            new_comp = 0
            for _, row in df_comp.iterrows():
                cid = str(row["component_id"]).strip()
                if cid not in existing_comp:
                    session.add(
                        SalaryComponent(
                            component_id=cid,
                            component_name=str(row["component_name"]).strip(),
                            component_type=str(row["component_type"]).strip(),
                            taxable=str(row["taxable"]).strip(),
                            calculation_rule=_clean_str(row.get("calculation_rule")),
                            is_fixed=str(row["is_fixed"]).strip(),
                        )
                    )
                    existing_comp.add(cid)
                    new_comp += 1
            session.commit()
            counts["salary_components"] = len(existing_comp)
            print(f"[Salary Components] {new_comp} inserted, total in DB: {len(existing_comp)}")

        # -------------------------------------------------------------
        # 10. Salary Revisions (LF-05)
        # -------------------------------------------------------------
        csv_rev_path = csv_dir / "salary_revisions.csv"
        if csv_rev_path.exists():
            df_rev = pd.read_csv(csv_rev_path)
            existing_rev = set(session.scalars(select(SalaryRevision.revision_id)).all())
            new_rev = 0
            rev_records = []
            for row in df_rev.to_dict(orient="records"):
                rid = str(row["revision_id"]).strip()
                eid = str(row["employee_id"]).strip()
                if rid not in existing_rev and eid in existing_emps:
                    rev_records.append(
                        {
                            "revision_id": rid,
                            "employee_id": eid,
                            "effective_from": _to_date(row["effective_from"]),
                            "revision_reason": _clean_str(row.get("revision_reason")),
                            "previous_annual_fixed": Decimal(str(row["previous_annual_fixed"]))
                            if pd.notna(row.get("previous_annual_fixed"))
                            else None,
                            "new_annual_fixed": Decimal(str(row["new_annual_fixed"])),
                            "pct_change": Decimal(str(row["pct_change"]))
                            if pd.notna(row.get("pct_change"))
                            else None,
                            "role_id_after": _clean_str(row.get("role_id_after")),
                            "approved_by": _clean_str(row.get("approved_by")),
                        }
                    )
                    existing_rev.add(rid)
                    new_rev += 1
            if rev_records:
                session.execute(insert(SalaryRevision), rev_records)
                session.commit()
            counts["salary_revisions"] = len(existing_rev)
            print(f"[Salary Revisions] {new_rev} inserted, total in DB: {len(existing_rev)}")

        # -------------------------------------------------------------
        # 11. Salary Structures (LF-05)
        # -------------------------------------------------------------
        csv_st_path = csv_dir / "salary_structures.csv"
        if csv_st_path.exists():
            df_st = pd.read_csv(csv_st_path)
            existing_st = set(session.scalars(select(SalaryStructure.structure_id)).all())
            new_st = 0
            st_records = []
            for row in df_st.to_dict(orient="records"):
                sid = str(row["structure_id"]).strip()
                eid = str(row["employee_id"]).strip()
                if sid not in existing_st and eid in existing_emps:
                    st_records.append(
                        {
                            "structure_id": sid,
                            "employee_id": eid,
                            "component_id": str(row["component_id"]).strip(),
                            "component_name": str(row["component_name"]).strip(),
                            "component_type": str(row["component_type"]).strip(),
                            "monthly_amount": Decimal(str(row["monthly_amount"])),
                            "effective_from": _to_date(row["effective_from"]),
                            "effective_to": _to_date(row.get("effective_to")),
                            "revision_id": _clean_str(row.get("revision_id")),
                        }
                    )
                    existing_st.add(sid)
                    new_st += 1
                    if len(st_records) >= 5000:
                        session.execute(insert(SalaryStructure), st_records)
                        session.commit()
                        st_records.clear()
            if st_records:
                session.execute(insert(SalaryStructure), st_records)
                session.commit()
            counts["salary_structures"] = len(existing_st)
            print(f"[Salary Structures] {new_st} inserted, total in DB: {len(existing_st)}")

        # -------------------------------------------------------------
        # 12. Statutory Rates, Tax Parameters, Tax Slabs (LF-07)
        # -------------------------------------------------------------
        csv_sr_path = csv_dir / "statutory_rates.csv"
        if csv_sr_path.exists():
            df_sr = pd.read_csv(csv_sr_path)
            existing_sr = set(session.scalars(select(StatutoryRate.parameter)).all())
            new_sr = 0
            for _, row in df_sr.iterrows():
                param = str(row["parameter"]).strip()
                if param not in existing_sr:
                    session.add(
                        StatutoryRate(
                            parameter=param,
                            value=Decimal(str(row["value"])),
                            unit=str(row["unit"]).strip(),
                            note=_clean_str(row.get("note")),
                            effective_from=_to_date(row["effective_from"]),
                        )
                    )
                    existing_sr.add(param)
                    new_sr += 1
            session.commit()
            counts["statutory_rates"] = len(existing_sr)
            print(f"[Statutory Rates] {new_sr} inserted, total in DB: {len(existing_sr)}")

        csv_tp_path = csv_dir / "tax_parameters.csv"
        if csv_tp_path.exists():
            df_tp = pd.read_csv(csv_tp_path)
            existing_tp = set(session.scalars(select(TaxParameter.parameter)).all())
            new_tp = 0
            for _, row in df_tp.iterrows():
                param = str(row["parameter"]).strip()
                if param not in existing_tp:
                    session.add(
                        TaxParameter(
                            parameter=param,
                            value=Decimal(str(row["value"])),
                            note=_clean_str(row.get("note")),
                        )
                    )
                    existing_tp.add(param)
                    new_tp += 1
            session.commit()
            counts["tax_parameters"] = len(existing_tp)
            print(f"[Tax Parameters] {new_tp} inserted, total in DB: {len(existing_tp)}")

        csv_ts_path = csv_dir / "tax_slabs.csv"
        if csv_ts_path.exists():
            df_ts = pd.read_csv(csv_ts_path)
            existing_ts = set(session.scalars(select(TaxSlab.slab_id)).all())
            new_ts = 0
            for _, row in df_ts.iterrows():
                sid = str(row["slab_id"]).strip()
                if sid not in existing_ts:
                    session.add(
                        TaxSlab(
                            slab_id=sid,
                            regime=str(row["regime"]).strip(),
                            financial_year=str(row["financial_year"]).strip(),
                            income_from=Decimal(str(row["income_from"])),
                            income_to=Decimal(str(row["income_to"])) if pd.notna(row.get("income_to")) else None,
                            rate_percent=Decimal(str(row["rate_percent"])),
                            effective_from=_to_date(row["effective_from"]),
                            note=_clean_str(row.get("note")),
                        )
                    )
                    existing_ts.add(sid)
                    new_ts += 1
            session.commit()
            counts["tax_slabs"] = len(existing_ts)
            print(f"[Tax Slabs] {new_ts} inserted, total in DB: {len(existing_ts)}")

        # -------------------------------------------------------------
        # 13. Payroll Runs & Payroll Items (LF-07 / LF-08)
        # -------------------------------------------------------------
        csv_pr_path = csv_dir / "payroll_runs.csv"
        if csv_pr_path.exists():
            df_pr = pd.read_csv(csv_pr_path)
            existing_pr = set(session.scalars(select(PayrollRun.run_id)).all())
            new_pr = 0
            for _, row in df_pr.iterrows():
                rid = str(row["run_id"]).strip()
                if rid not in existing_pr:
                    session.add(
                        PayrollRun(
                            run_id=rid,
                            period_start=_to_date(row["period_start"]),
                            period_end=_to_date(row["period_end"]),
                            pay_date=_to_date(row.get("pay_date")),
                            employees_paid=int(row["employees_paid"]),
                            total_gross=Decimal(str(row["total_gross"])),
                            total_deductions=Decimal(str(row["total_deductions"])),
                            total_net=Decimal(str(row["total_net"])),
                            total_employer_contributions=Decimal(str(row["total_employer_contributions"])),
                            total_employer_cost=Decimal(str(row["total_employer_cost"])),
                            status=str(row["status"]).strip(),
                            run_by=_clean_str(row.get("run_by")),
                            approved_by=_clean_str(row.get("approved_by")),
                            approved_at=_clean_str(row.get("approved_at")),
                            idempotency_key=_clean_str(row.get("idempotency_key")),
                            journal_entry_id=_clean_str(row.get("journal_entry_id")),
                            calculation_version=_clean_str(row.get("calculation_version")),
                        )
                    )
                    existing_pr.add(rid)
                    new_pr += 1
            session.commit()
            counts["payroll_runs"] = len(existing_pr)
            print(f"[Payroll Runs] {new_pr} inserted, total in DB: {len(existing_pr)}")

        csv_pi_path = csv_dir / "payroll_items.csv"
        if csv_pi_path.exists():
            df_pi = pd.read_csv(csv_pi_path)
            existing_pi = set(session.scalars(select(PayrollItem.payroll_item_id)).all())
            new_pi = 0
            pi_records = []
            for row in df_pi.to_dict(orient="records"):
                piid = str(row["payroll_item_id"]).strip()
                eid = str(row["employee_id"]).strip()
                if piid not in existing_pi and eid in existing_emps:
                    pi_records.append(
                        {
                            "payroll_item_id": piid,
                            "run_id": str(row["run_id"]).strip(),
                            "employee_id": eid,
                            "period_start": _to_date(row["period_start"]),
                            "period_end": _to_date(row["period_end"]),
                            "department_id": str(row["department_id"]).strip(),
                            "role_id": str(row["role_id"]).strip(),
                            "calendar_days": int(row["calendar_days"]),
                            "days_employed": int(row["days_employed"]),
                            "lop_days": Decimal(str(row["lop_days"])),
                            "payable_days": Decimal(str(row["payable_days"])),
                            "monthly_fixed_gross": Decimal(str(row["monthly_fixed_gross"])),
                            "basic": Decimal(str(row["basic"])),
                            "hra": Decimal(str(row["hra"])),
                            "conveyance": Decimal(str(row["conveyance"])),
                            "medical": Decimal(str(row["medical"])),
                            "special_allowance": Decimal(str(row["special_allowance"])),
                            "earned_fixed_pay": Decimal(str(row["earned_fixed_pay"])),
                            "overtime_hours_paid": Decimal(str(row["overtime_hours_paid"])),
                            "overtime_pay": Decimal(str(row["overtime_pay"])),
                            "variable_pay": Decimal(str(row["variable_pay"])),
                            "variable_pay_type": _clean_str(row.get("variable_pay_type")),
                            "gross_pay": Decimal(str(row["gross_pay"])),
                            "pf_employee": Decimal(str(row["pf_employee"])),
                            "esi_employee": Decimal(str(row["esi_employee"])),
                            "professional_tax": Decimal(str(row["professional_tax"])),
                            "tds": Decimal(str(row["tds"])),
                            "other_deductions": Decimal(str(row["other_deductions"])),
                            "total_deductions": Decimal(str(row["total_deductions"])),
                            "net_pay": Decimal(str(row["net_pay"])),
                            "pf_employer": Decimal(str(row["pf_employer"])),
                            "esi_employer": Decimal(str(row["esi_employer"])),
                            "employer_cost": Decimal(str(row["employer_cost"])),
                            "calculation_note": _clean_str(row.get("calculation_note")),
                        }
                    )
                    existing_pi.add(piid)
                    new_pi += 1
                    if len(pi_records) >= 5000:
                        session.execute(insert(PayrollItem), pi_records)
                        session.commit()
                        pi_records.clear()
            if pi_records:
                session.execute(insert(PayrollItem), pi_records)
                session.commit()
            counts["payroll_items"] = len(existing_pi)
            print(f"[Payroll Items] {new_pi} inserted, total in DB: {len(existing_pi)}")

        # -------------------------------------------------------------
        # 14. Chart of Accounts, Journal Entries & Journal Lines (LF-09)
        # -------------------------------------------------------------
        csv_coa_path = csv_dir / "chart_of_accounts.csv"
        if csv_coa_path.exists():
            df_coa = pd.read_csv(csv_coa_path)
            existing_coa = set(session.scalars(select(ChartOfAccount.account_code)).all())
            new_coa = 0
            for _, row in df_coa.iterrows():
                acode = int(row["account_code"])
                if acode not in existing_coa:
                    pcode = int(float(row["parent_code"])) if pd.notna(row.get("parent_code")) else None
                    session.add(
                        ChartOfAccount(
                            account_code=acode,
                            account_name=str(row["account_name"]).strip(),
                            account_type=str(row["account_type"]).strip(),
                            normal_balance=str(row["normal_balance"]).strip(),
                            parent_code=pcode,
                            is_group=str(row["is_group"]).strip(),
                            statement=str(row["statement"]).strip(),
                            is_active=str(row["is_active"]).strip(),
                        )
                    )
                    existing_coa.add(acode)
                    new_coa += 1
            session.commit()
            counts["chart_of_accounts"] = len(existing_coa)
            print(f"[Chart of Accounts] {new_coa} inserted, total in DB: {len(existing_coa)}")

        csv_je_path = csv_dir / "journal_entries.csv"
        csv_jl_path = csv_dir / "journal_lines.csv"
        if csv_je_path.exists() and csv_jl_path.exists():
            df_je = pd.read_csv(csv_je_path)
            existing_je = set(session.scalars(select(JournalEntry.entry_id)).all())
            new_je = 0
            je_records = []
            # When seeding the full dataset, we let post_payroll_run_to_ledger("PR-2025-04") post JE-000105 directly
            skip_je_for_engine = "JE-000105" if employee_limit is None else None
            for row in df_je.to_dict(orient="records"):
                eid = str(row["entry_id"]).strip()
                if eid == skip_je_for_engine:
                    continue
                if eid not in existing_je:
                    je_records.append(
                        {
                            "entry_id": eid,
                            "entry_date": _to_date(row["entry_date"]),
                            "posting_period": str(row["posting_period"]).strip(),
                            "financial_year": str(row["financial_year"]).strip(),
                            "description": str(row["description"]).strip(),
                            "source_type": str(row["source_type"]).strip(),
                            "source_id": str(row["source_id"]).strip(),
                            "status": str(row["status"]).strip(),
                            "total_debit": Decimal(str(row["total_debit"])),
                            "total_credit": Decimal(str(row["total_credit"])),
                            "reversal_of_source_id": _clean_str(row.get("reversal_of_source_id")),
                            "created_by": _clean_str(row.get("created_by")),
                            "created_at": _clean_str(row.get("created_at")),
                        }
                    )
                    existing_je.add(eid)
                    new_je += 1
            if je_records:
                session.execute(insert(JournalEntry), je_records)
                session.commit()

            df_jl = pd.read_csv(csv_jl_path)
            existing_jl = set(session.scalars(select(JournalLine.line_id)).all())
            new_jl = 0
            jl_records = []
            for row in df_jl.to_dict(orient="records"):
                lid = str(row["line_id"]).strip()
                eid = str(row["entry_id"]).strip()
                if eid == skip_je_for_engine:
                    continue
                if lid not in existing_jl and eid in existing_je:
                    jl_records.append(
                        {
                            "line_id": lid,
                            "entry_id": eid,
                            "line_no": int(row["line_no"]),
                            "account_code": int(row["account_code"]),
                            "debit": Decimal(str(row["debit"])),
                            "credit": Decimal(str(row["credit"])),
                            "cost_center_department_id": _clean_str(row.get("cost_center_department_id")),
                            "line_description": _clean_str(row.get("line_description")),
                        }
                    )
                    existing_jl.add(lid)
                    new_jl += 1
                    if len(jl_records) >= 5000:
                        session.execute(insert(JournalLine), jl_records)
                        session.commit()
                        jl_records.clear()
            if jl_records:
                session.execute(insert(JournalLine), jl_records)
                session.commit()

            # Post PR-2025-04 (JE-000105) via our own double-entry ledger engine when full payroll items exist
            if employee_limit is None and "JE-000105" not in existing_je:
                posted = post_payroll_run_to_ledger(session, "PR-2025-04", entry_id="JE-000105")
                existing_je.add(posted["entry_id"])
                new_je += 1
                new_jl += len(posted["lines"])

            total_jl = session.scalar(select(func.count(JournalLine.line_id))) or 0
            counts["journal_entries"] = len(existing_je)
            counts["journal_lines"] = total_jl
            print(f"[Journal Entries] {new_je} inserted, total in DB: {len(existing_je)}")
            print(f"[Journal Lines] {new_jl} inserted, total in DB: {total_jl}")

        # -------------------------------------------------------------
        # 15. Clients, Invoices, Invoice Items & Invoice Payments (LF-10)
        # -------------------------------------------------------------
        csv_cl_path = csv_dir / "clients.csv"
        if csv_cl_path.exists():
            df_cl = pd.read_csv(csv_cl_path)
            existing_cl = set(session.scalars(select(Client.client_id)).all())
            new_cl = 0
            for _, row in df_cl.iterrows():
                cid = str(row["client_id"]).strip()
                if cid not in existing_cl:
                    session.add(
                        Client(
                            client_id=cid,
                            client_name=str(row["client_name"]).strip(),
                            industry=str(row["industry"]).strip(),
                            city=str(row["city"]).strip(),
                            state_or_region=str(row["state_or_region"]).strip(),
                            country=str(row["country"]).strip(),
                            client_type=str(row["client_type"]).strip(),
                            gst_registration=_clean_str(row.get("gst_registration")),
                            payment_terms_days=int(row["payment_terms_days"]),
                            payment_behaviour=_clean_str(row.get("payment_behaviour")),
                            primary_service_line=int(row["primary_service_line"]),
                            contact_email=str(row["contact_email"]).strip(),
                            onboarded_on=_to_date(row["onboarded_on"]),
                            is_active=str(row["is_active"]).strip(),
                        )
                    )
                    existing_cl.add(cid)
                    new_cl += 1
            session.commit()
            counts["clients"] = len(existing_cl)
            print(f"[Clients] {new_cl} inserted, total in DB: {len(existing_cl)}")

        csv_inv_path = csv_dir / "invoices.csv"
        if csv_inv_path.exists():
            df_inv = pd.read_csv(csv_inv_path)
            existing_inv = set(session.scalars(select(Invoice.invoice_id)).all())
            new_inv = 0
            inv_records = []
            for row in df_inv.to_dict(orient="records"):
                iid = str(row["invoice_id"]).strip()
                if iid not in existing_inv:
                    inv_records.append(
                        {
                            "invoice_id": iid,
                            "invoice_number": str(row["invoice_number"]).strip(),
                            "client_id": str(row["client_id"]).strip(),
                            "invoice_date": _to_date(row["invoice_date"]),
                            "due_date": _to_date(row["due_date"]),
                            "service_line_account": int(row["service_line_account"]),
                            "currency": str(row["currency"]).strip(),
                            "subtotal": Decimal(str(row["subtotal"])),
                            "gst_rate_percent": Decimal(str(row["gst_rate_percent"])),
                            "gst_amount": Decimal(str(row["gst_amount"])),
                            "total_amount": Decimal(str(row["total_amount"])),
                            "amount_paid": Decimal(str(row["amount_paid"])),
                            "balance_due": Decimal(str(row["balance_due"])),
                            "status": str(row["status"]).strip(),
                            "last_payment_date": _to_date(row.get("last_payment_date")),
                            "po_number": _clean_str(row.get("po_number")),
                            "carried_in_from_prior_period": str(row["carried_in_from_prior_period"]).strip(),
                            "created_by": _clean_str(row.get("created_by")),
                            "created_at": _clean_str(row.get("created_at")),
                            "ledger_entry_id": _clean_str(row.get("ledger_entry_id")),
                        }
                    )
                    existing_inv.add(iid)
                    new_inv += 1
            if inv_records:
                session.execute(insert(Invoice), inv_records)
                session.commit()
            counts["invoices"] = len(existing_inv)
            print(f"[Invoices] {new_inv} inserted, total in DB: {len(existing_inv)}")

        csv_ii_path = csv_dir / "invoice_items.csv"
        if csv_ii_path.exists():
            df_ii = pd.read_csv(csv_ii_path)
            existing_ii = set(session.scalars(select(InvoiceItem.invoice_item_id)).all())
            new_ii = 0
            ii_records = []
            for row in df_ii.to_dict(orient="records"):
                iiid = str(row["invoice_item_id"]).strip()
                if iiid not in existing_ii:
                    ii_records.append(
                        {
                            "invoice_item_id": iiid,
                            "invoice_id": str(row["invoice_id"]).strip(),
                            "line_no": int(row["line_no"]),
                            "description": str(row["description"]).strip(),
                            "quantity": Decimal(str(row["quantity"])),
                            "unit_price": Decimal(str(row["unit_price"])),
                            "amount": Decimal(str(row["amount"])),
                            "revenue_account": int(row["revenue_account"]),
                        }
                    )
                    existing_ii.add(iiid)
                    new_ii += 1
            if ii_records:
                session.execute(insert(InvoiceItem), ii_records)
                session.commit()
            counts["invoice_items"] = len(existing_ii)
            print(f"[Invoice Items] {new_ii} inserted, total in DB: {len(existing_ii)}")

        csv_ip_path = csv_dir / "invoice_payments.csv"
        if csv_ip_path.exists():
            df_ip = pd.read_csv(csv_ip_path)
            existing_ip = set(session.scalars(select(InvoicePayment.payment_id)).all())
            new_ip = 0
            ip_records = []
            for row in df_ip.to_dict(orient="records"):
                pid = str(row["payment_id"]).strip()
                if pid not in existing_ip:
                    ip_records.append(
                        {
                            "payment_id": pid,
                            "invoice_id": str(row["invoice_id"]).strip(),
                            "payment_date": _to_date(row["payment_date"]),
                            "amount": Decimal(str(row["amount"])),
                            "payment_mode": str(row["payment_mode"]).strip(),
                            "reference_no": _clean_str(row.get("reference_no")),
                            "received_by": _clean_str(row.get("received_by")),
                            "ledger_entry_id": _clean_str(row.get("ledger_entry_id")),
                        }
                    )
                    existing_ip.add(pid)
                    new_ip += 1
            if ip_records:
                session.execute(insert(InvoicePayment), ip_records)
                session.commit()
            counts["invoice_payments"] = len(existing_ip)
            print(f"[Invoice Payments] {new_ip} inserted, total in DB: {len(existing_ip)}")

    if session is not None:
        _run_seed(session)
    else:
        eng = get_engine()
        Base.metadata.create_all(eng)
        with Session(eng) as s:
            _run_seed(s)

    if do_export:
        print("\n=== Generating CSV Exports ===")
        export_counts = export_all_to_csv(session=session)
        print(f"Exported tables: {export_counts}")

    elapsed = time.perf_counter() - t0
    print(f"\n=== Seeding Finished Successfully in {elapsed:.2f}s ===")
    return counts


def main():
    parser = argparse.ArgumentParser(description="Seed LedgerForge database with master dataset")
    default_file = (
        ROOT / "data" / "seed" / "01_LedgerForge_Python_Master_Dataset.xlsx"
        if (ROOT / "data" / "seed" / "01_LedgerForge_Python_Master_Dataset.xlsx").exists()
        else ROOT / "01_LedgerForge_Python_Master_Dataset.xlsx"
    )
    parser.add_argument("--file", type=Path, default=default_file, help="Path to Excel dataset")
    parser.add_argument("--days", type=int, default=60, help="Days of attendance (when --limit is set)")
    parser.add_argument("--limit", type=int, default=None, help="Employee limit for speed (optional)")
    parser.add_argument("--chunk-size", type=int, default=10000, help="Chunk size for loading attendance.csv")
    parser.add_argument("--no-export", action="store_true", help="Skip CSV export")
    parser.add_argument("--reset", action="store_true", help="Reset/clear existing data before seeding")

    args = parser.parse_args()

    if args.reset:
        engine = get_engine()
        Base.metadata.create_all(engine)
        with Session(engine) as s:
            print("Resetting existing tables...")
            s.query(InvoicePayment).delete()
            s.query(InvoiceItem).delete()
            s.query(Invoice).delete()
            s.query(Client).delete()
            s.query(JournalLine).delete()
            s.query(JournalEntry).delete()
            s.query(ChartOfAccount).delete()
            s.query(PayrollItem).delete()
            s.query(PayrollRun).delete()
            s.query(TaxSlab).delete()
            s.query(TaxParameter).delete()
            s.query(StatutoryRate).delete()
            s.query(LeaveRequest).delete()
            s.query(LeaveBalance).delete()
            s.query(LeaveType).delete()
            s.query(Holiday).delete()
            s.query(SalaryStructure).delete()
            s.query(SalaryRevision).delete()
            s.query(SalaryComponent).delete()
            s.query(EmployeeAssignment).delete()
            s.query(Attendance).delete()
            s.query(Salary).delete()
            s.query(Employee).delete()
            s.query(Role).delete()
            s.query(Department).delete()
            s.commit()
            print("Tables cleared.")

    seed_master_dataset(
        xlsx_path=args.file,
        attendance_days=args.days,
        employee_limit=args.limit,
        do_export=not args.no_export,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
