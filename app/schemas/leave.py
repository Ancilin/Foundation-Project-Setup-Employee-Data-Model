"""Pydantic schemas for Leave types, balances, requests, and holidays (LF-06)."""

from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class HolidayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    holiday_date: date
    holiday_name: str
    holiday_type: str
    weekday: str
    falls_on_weekend: str
    calendar_note: str | None = None


class LeaveTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    leave_type_code: str
    leave_type_name: str
    pay_type: str
    annual_quota_days: int
    prorated_for_joiners: str
    carry_forward_allowed: str
    max_carry_forward_days: int
    policy_note: str | None = None


class LeaveBalanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    as_of_date: date
    financial_year: str
    cl_entitlement: Decimal
    cl_used: Decimal
    cl_balance: Decimal
    sl_entitlement: Decimal
    sl_used: Decimal
    sl_balance: Decimal
    el_used_fy: Decimal
    el_balance: Decimal
    pending_days: Decimal


class LeaveApplyRequest(BaseModel):
    employee_id: str = Field(..., min_length=1, max_length=10)
    leave_type_code: Literal["CL", "SL", "EL", "ML", "BL", "LOP"]
    start_date: date
    end_date: date
    reason: str | None = Field(None, max_length=255)
    applied_on: date | None = None
    is_half_day: bool = False
    half_day_session: Literal["FIRST_HALF", "SECOND_HALF"] | None = None


class LeaveDecisionRequest(BaseModel):
    approver_id: str = Field(..., min_length=1, max_length=10)
    decided_on: date | None = None


class LeaveRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    leave_request_id: str
    employee_id: str
    leave_type_code: str
    start_date: date
    end_date: date
    days: Decimal
    reason: str | None = None
    status: str
    applied_on: date
    approver_id: str | None = None
    decided_on: date | None = None
