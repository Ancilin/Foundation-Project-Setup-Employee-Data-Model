"""Tests for LF-06: Attendance, monthly summary (3 hand-checked employees), MISSING_CHECKOUT,
holiday/weekend exclusion, and leave apply/approve/reject workflows.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Attendance,
    Department,
    Employee,
    Holiday,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    Role,
)
from app.services.attendance_service import count_working_days, monthly_summary
from scripts.seed import ROOT, load_attendance_in_chunks

CSV_DIR = ROOT / "data" / "csv"


@pytest.fixture
def seed_lf06_reference_and_three_employees(session: Session):
    """Seed holidays, leave_types, and the 3 hand-checked employees with their real CSV attendance rows."""
    # 1. Reference tables: departments & roles from CSV
    df_depts = pd.read_csv(CSV_DIR / "departments.csv")
    for _, r in df_depts.iterrows():
        session.add(
            Department(
                department_id=str(r["department_id"]).strip(),
                department_name=str(r["department_name"]).strip(),
                cost_center=str(r["cost_center"]).strip(),
                description=str(r["description"]).strip() if pd.notna(r.get("description")) else None,
            )
        )

    df_roles = pd.read_csv(CSV_DIR / "roles.csv")
    for _, r in df_roles.iterrows():
        session.add(
            Role(
                role_id=str(r["role_id"]).strip(),
                department_id=str(r["department_id"]).strip(),
                role_title=str(r["role_title"]).strip(),
                level=int(r["level"]),
                grade=str(r["grade"]).strip(),
                band_min_annual=float(r["band_min_annual"]),
                band_mid_annual=float(r["band_mid_annual"]),
                band_max_annual=float(r["band_max_annual"]),
                overtime_eligible=(str(r.get("overtime_eligible", "")).upper() == "Y"),
            )
        )

    df_hol = pd.read_csv(CSV_DIR / "holidays.csv")
    for _, r in df_hol.iterrows():
        session.add(
            Holiday(
                holiday_date=date.fromisoformat(str(r["holiday_date"])[:10]),
                holiday_name=str(r["holiday_name"]).strip(),
                holiday_type=str(r["holiday_type"]).strip(),
                weekday=str(r["weekday"]).strip(),
                falls_on_weekend=str(r["falls_on_weekend"]).strip(),
                calendar_note=str(r["calendar_note"]).strip() if pd.notna(r.get("calendar_note")) else None,
            )
        )

    df_lt = pd.read_csv(CSV_DIR / "leave_types.csv")
    for _, r in df_lt.iterrows():
        session.add(
            LeaveType(
                leave_type_code=str(r["leave_type_code"]).strip(),
                leave_type_name=str(r["leave_type_name"]).strip(),
                pay_type=str(r["pay_type"]).strip(),
                annual_quota_days=int(r["annual_quota_days"]),
                prorated_for_joiners=str(r["prorated_for_joiners"]).strip(),
                carry_forward_allowed=str(r["carry_forward_allowed"]).strip(),
                max_carry_forward_days=int(r["max_carry_forward_days"]),
                policy_note=str(r["policy_note"]).strip() if pd.notna(r.get("policy_note")) else None,
            )
        )
    session.commit()

    # 2. Seed the 3 target employees + 1 approver manager (EMP-0002 is also an employee)
    target_ids = {"EMP-0002", "EMP-0011", "EMP-0148"}
    df_emps = pd.read_csv(CSV_DIR / "employees.csv")
    df_sub_emps = df_emps[df_emps["employee_id"].isin(target_ids)]
    for _, r in df_sub_emps.iterrows():
        session.add(
            Employee(
                employee_id=str(r["employee_id"]).strip(),
                first_name=str(r["first_name"]).strip(),
                last_name=str(r["last_name"]).strip(),
                work_email=str(r["work_email"]).strip(),
                gender=str(r["gender"]).strip(),
                date_of_birth=date.fromisoformat(str(r["date_of_birth"])[:10]),
                hire_date=date.fromisoformat(str(r["hire_date"])[:10]),
                exit_date=date.fromisoformat(str(r["exit_date"])[:10]) if pd.notna(r.get("exit_date")) else None,
                employment_status=str(r["employment_status"]).strip(),
                employment_type=str(r["employment_type"]).strip(),
                department_id=str(r["department_id"]).strip(),
                role_id=str(r["role_id"]).strip(),
                manager_id=None,
                work_location=str(r["work_location"]).strip(),
                work_mode=str(r["work_mode"]).strip(),
            )
        )
    session.commit()

    # 3. Seed leave balances for the 3 employees from CSV
    df_lb = pd.read_csv(CSV_DIR / "leave_balances.csv")
    for _, r in df_lb[df_lb["employee_id"].isin(target_ids)].iterrows():
        session.add(
            LeaveBalance(
                employee_id=str(r["employee_id"]).strip(),
                as_of_date=date.fromisoformat(str(r["as_of_date"])[:10]),
                financial_year=str(r["financial_year"]).strip(),
                cl_entitlement=Decimal(str(r["cl_entitlement"])),
                cl_used=Decimal(str(r["cl_used"])),
                cl_balance=Decimal(str(r["cl_balance"])),
                sl_entitlement=Decimal(str(r["sl_entitlement"])),
                sl_used=Decimal(str(r["sl_used"])),
                sl_balance=Decimal(str(r["sl_balance"])),
                el_used_fy=Decimal(str(r["el_used_fy"])),
                el_balance=Decimal(str(r["el_balance"])),
                pending_days=Decimal(str(r["pending_days"])),
            )
        )
    session.commit()
    return target_ids


def test_hand_count_matches_monthly_summary_for_three_employees(
    session: Session,
    client: TestClient,
    seed_lf06_reference_and_three_employees,
):
    """Verify monthly_summary equals the exact hand-counted CSV figures for 3 employees."""
    target_ids = seed_lf06_reference_and_three_employees
    inserted = load_attendance_in_chunks(
        session=session,
        csv_path=CSV_DIR / "attendance.csv",
        chunk_size=25000,
        valid_emps=target_ids,
    )
    assert inserted > 0
    # Hand-checked Employee 1: EMP-0002 in 2025-05
    # 21 working days (May 1 Labour Day holiday excluded): 2 PRESENT, 18 WFH, 1 HALF_DAY_UNPAID (0.5 LOP), 2 late, 0.00 OT
    s1 = monthly_summary(session, "EMP-0002", "2025-05")
    assert s1["total_working_days"] == 21
    assert s1["days_present"] == 2
    assert s1["days_wfh"] == 18
    assert s1["days_absent"] == 0
    assert s1["paid_leave_days"] == 0
    assert s1["half_days"] == 1
    assert s1["lop_days"] == Decimal("0.50")
    assert s1["late_days"] == 2
    assert s1["overtime_hours"] == Decimal("0.00")
    assert s1["missing_checkout_count"] == 0

    # Also verify HTTP endpoint agrees
    resp1 = client.get("/attendance/EMP-0002/summary/2025-05")
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["days_present"] == 2
    assert body1["days_wfh"] == 18
    assert body1["half_days"] == 1
    assert Decimal(str(body1["lop_days"])) == Decimal("0.50")
    assert body1["late_days"] == 2

    # Hand-checked Employee 2: EMP-0011 in 2026-01
    # 19 working days (Jan 1, Jan 14, Jan 26 holidays excluded): 9 PRESENT, 8 WFH, 1 PAID_LEAVE, 1 ABSENT_LOP, 1 late, 4.00 OT
    s2 = monthly_summary(session, "EMP-0011", "2026-01")
    assert s2["total_working_days"] == 19
    assert s2["days_present"] == 9
    assert s2["days_wfh"] == 8
    assert s2["days_absent"] == 1
    assert s2["absent_lop_days"] == 1
    assert s2["paid_leave_days"] == 1
    assert s2["half_days"] == 0
    assert s2["lop_days"] == Decimal("1.00")
    assert s2["late_days"] == 1
    assert s2["overtime_hours"] == Decimal("4.00")
    assert s2["missing_checkout_count"] == 0

    # Hand-checked Employee 3: EMP-0148 in 2025-12
    # 22 working days (Dec 25 Christmas holiday excluded): 9 PRESENT (1 with MISSING_CHECKOUT), 10 WFH, 2 PAID_LEAVE, 1 ABSENT_LOP, 1 late, 0.00 OT
    s3 = monthly_summary(session, "EMP-0148", "2025-12")
    assert s3["total_working_days"] == 22
    assert s3["days_present"] == 9
    assert s3["days_wfh"] == 10
    assert s3["days_absent"] == 1
    assert s3["paid_leave_days"] == 2
    assert s3["half_days"] == 0
    assert s3["lop_days"] == Decimal("1.00")
    assert s3["late_days"] == 1
    assert s3["overtime_hours"] == Decimal("0.00")
    assert s3["missing_checkout_count"] == 1


def test_missing_checkout_rule_handling(
    session: Session,
    client: TestClient,
    seed_lf06_reference_and_three_employees,
):
    """Verify recording a row with missing check-out sets MISSING_CHECKOUT, zeroes OT, and honors status."""
    resp = client.post(
        "/attendance",
        json={
            "employee_id": "EMP-0002",
            "attendance_date": "2026-10-05",
            "status": "PRESENT",
            "check_in": "09:50",
            "check_out": None,
            "overtime_hours": "3.00",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["data_quality_flag"] == "MISSING_CHECKOUT"
    assert data["hours_worked"] is None
    assert Decimal(str(data["overtime_hours"])) == Decimal("0.00")
    assert data["late_flag"] == "Y"

    summary = monthly_summary(session, "EMP-0002", "2026-10")
    assert summary["days_present"] == 1
    assert summary["days_absent"] == 0
    assert summary["late_days"] == 1
    assert summary["overtime_hours"] == Decimal("0.00")
    assert summary["missing_checkout_count"] == 1


def test_working_day_counting_skips_weekends_and_holidays(
    session: Session,
    seed_lf06_reference_and_three_employees,
):
    """Weekends (Sat/Sun) and company holidays (e.g. 2025-04-14 and 2025-04-18) are never counted as leave days."""
    # From Friday 2025-04-11 to Monday 2025-04-21 (11 calendar days):
    # - Weekends: Apr 12, 13, 19, 20 (4 days)
    # - Holidays: Apr 14 (Ambedkar Jayanti), Apr 18 (Good Friday) (2 days)
    # - Working days: Apr 11, 15, 16, 17, 21 -> exactly 5 working days
    days = count_working_days(session, date(2025, 4, 11), date(2025, 4, 21))
    assert days == Decimal("5.00")

    # Weekend-only span returns 0 working days
    weekend_days = count_working_days(session, date(2025, 4, 12), date(2025, 4, 13))
    assert weekend_days == Decimal("0.00")


def test_leave_apply_approve_reject_and_insufficient_balance(
    client: TestClient,
    seed_lf06_reference_and_three_employees,
):
    """Test full leave lifecycle:
    1. Apply leave across a weekend + holiday -> counts only working days, adds to pending_days.
    2. Approve leave -> reduces balance and clears pending_days.
    3. Reject leave -> leaves balance intact and clears pending_days.
    4. Insufficient balance -> rejected with 400 INSUFFICIENT_BALANCE.
    5. Half-day leave -> deducts 0.50 days on approval.
    """
    # Check initial balance for EMP-0002 (CL balance = 12.00)
    bal_init = client.get("/leave/balances/EMP-0002").json()
    assert Decimal(str(bal_init["cl_balance"])) == Decimal("12.00")

    # 1. Apply for CL from 2025-04-11 to 2025-04-21 (5 working days after skipping 2 weekends + 2 holidays)
    apply_resp = client.post(
        "/leave/requests",
        json={
            "employee_id": "EMP-0002",
            "leave_type_code": "CL",
            "start_date": "2025-04-11",
            "end_date": "2025-04-21",
            "reason": "Family trip",
        },
    )
    assert apply_resp.status_code == 201
    req1 = apply_resp.json()
    assert req1["status"] == "Pending"
    assert Decimal(str(req1["days"])) == Decimal("5.00")

    # Balance should still be 12.00, pending_days = 5.00
    bal_pending = client.get("/leave/balances/EMP-0002").json()
    assert Decimal(str(bal_pending["cl_balance"])) == Decimal("12.00")
    assert Decimal(str(bal_pending["pending_days"])) == Decimal("5.00")

    # 2. Approve the leave request
    approve_resp = client.post(
        f"/leave/requests/{req1['leave_request_id']}/approve",
        json={"approver_id": "EMP-0011", "decided_on": "2025-04-10"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "Approved"

    # Balance should now be reduced: 12.00 - 5.00 = 7.00, cl_used = 5.00, pending_days = 0.00
    bal_after_approve = client.get("/leave/balances/EMP-0002").json()
    assert Decimal(str(bal_after_approve["cl_balance"])) == Decimal("7.00")
    assert Decimal(str(bal_after_approve["cl_used"])) == Decimal("5.00")
    assert Decimal(str(bal_after_approve["pending_days"])) == Decimal("0.00")

    # 3. Apply and then Reject a 2-day SL request
    apply_sl = client.post(
        "/leave/requests",
        json={
            "employee_id": "EMP-0002",
            "leave_type_code": "SL",
            "start_date": "2025-05-05",
            "end_date": "2025-05-06",
            "reason": "Medical checkup",
        },
    )
    assert apply_sl.status_code == 201
    req2 = apply_sl.json()
    assert Decimal(str(req2["days"])) == Decimal("2.00")

    reject_resp = client.post(
        f"/leave/requests/{req2['leave_request_id']}/reject",
        json={"approver_id": "EMP-0011", "decided_on": "2025-05-04"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "Rejected"

    # SL balance must remain 12.00
    bal_after_reject = client.get("/leave/balances/EMP-0002").json()
    assert Decimal(str(bal_after_reject["sl_balance"])) == Decimal("12.00")
    assert Decimal(str(bal_after_reject["pending_days"])) == Decimal("0.00")

    # 4. Attempt to apply for 10 days of CL when only 7.00 remain -> rejected (400 INSUFFICIENT_BALANCE)
    insufficient_resp = client.post(
        "/leave/requests",
        json={
            "employee_id": "EMP-0002",
            "leave_type_code": "CL",
            "start_date": "2025-06-02",
            "end_date": "2025-06-13",
            "reason": "Too many days",
        },
    )
    assert insufficient_resp.status_code == 400
    assert insufficient_resp.json()["error_code"] == "INSUFFICIENT_BALANCE"

    # 5. Half-day leave support (0.50 working day)
    half_day_resp = client.post(
        "/leave/requests",
        json={
            "employee_id": "EMP-0002",
            "leave_type_code": "CL",
            "start_date": "2025-06-02",
            "end_date": "2025-06-02",
            "is_half_day": True,
            "half_day_session": "FIRST_HALF",
            "reason": "Dentist appointment",
        },
    )
    assert half_day_resp.status_code == 201
    req_half = half_day_resp.json()
    assert Decimal(str(req_half["days"])) == Decimal("0.50")

    client.post(
        f"/leave/requests/{req_half['leave_request_id']}/approve",
        json={"approver_id": "EMP-0011"},
    )
    bal_final = client.get("/leave/balances/EMP-0002").json()
    assert Decimal(str(bal_final["cl_balance"])) == Decimal("6.50")
    assert Decimal(str(bal_final["cl_used"])) == Decimal("5.50")
