"""Employee schemas for creation, update, and responses."""

from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


GenderType = Literal["Male", "Female", "Other"]
EmploymentStatusType = Literal["Active", "Resigned", "Terminated", "Contract Ended"]
EmploymentTypeType = Literal["Permanent", "Fixed-Term Contract"]
WorkModeType = Literal["Onsite", "Hybrid", "Remote"]


class EmployeeBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=80, description="First name")
    last_name: str = Field(..., min_length=1, max_length=80, description="Last name")
    work_email: EmailStr = Field(..., description="Unique corporate work email")
    gender: GenderType
    date_of_birth: date
    hire_date: date
    exit_date: date | None = None
    employment_status: EmploymentStatusType = "Active"
    employment_type: EmploymentTypeType = "Permanent"
    work_location: str = Field(..., min_length=1, max_length=80)
    work_mode: WorkModeType
    department_id: str = Field(..., min_length=1, max_length=10)
    role_id: str = Field(..., min_length=1, max_length=10)
    manager_id: str | None = None

    @field_validator("first_name", "last_name", "work_location", mode="before")
    @classmethod
    def strip_and_check_non_empty(cls, v: str) -> str:
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("Value cannot be blank or empty whitespace")
            return stripped
        return v

    @field_validator("hire_date")
    @classmethod
    def hire_date_not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Hire date cannot be in the future")
        return v


class EmployeeCreate(EmployeeBase):
    employee_id: str | None = Field(
        None,
        description="Optional custom ID (e.g. EMP-0800). If omitted, generated automatically.",
        max_length=10,
    )


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=80)
    last_name: str | None = Field(None, min_length=1, max_length=80)
    work_email: EmailStr | None = None
    gender: GenderType | None = None
    date_of_birth: date | None = None
    hire_date: date | None = None
    exit_date: date | None = None
    employment_status: EmploymentStatusType | None = None
    employment_type: EmploymentTypeType | None = None
    work_location: str | None = Field(None, min_length=1, max_length=80)
    work_mode: WorkModeType | None = None
    department_id: str | None = Field(None, min_length=1, max_length=10)
    role_id: str | None = Field(None, min_length=1, max_length=10)
    manager_id: str | None = None

    @field_validator("first_name", "last_name", "work_location", mode="before")
    @classmethod
    def strip_and_check_non_empty(cls, v: str | None) -> str | None:
        if v is not None and isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("Value cannot be blank or empty whitespace")
            return stripped
        return v

    @field_validator("hire_date")
    @classmethod
    def hire_date_not_in_future(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("Hire date cannot be in the future")
        return v


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    first_name: str
    last_name: str
    full_name: str
    work_email: str
    gender: str
    date_of_birth: date
    hire_date: date
    exit_date: date | None = None
    employment_status: str
    employment_type: str
    work_location: str
    work_mode: str
    department_id: str
    role_id: str
    manager_id: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
