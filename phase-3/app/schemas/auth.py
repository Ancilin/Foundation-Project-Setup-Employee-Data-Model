"""Pydantic schemas for JWT Authentication, Users, and Role-Based Access Matrix (LF-13)."""

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username (email), user_id (e.g. U-0099), or employee_id (e.g. EMP-0099)")
    password: str = Field(..., min_length=1, description="User password (demo default: DemoPass@123)")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    user_id: str
    employee_id: str
    username: str
    role: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    employee_id: str
    username: str
    role: str
    is_active: str
    mfa_enabled: str
    last_login_at: str | None = None
    created_at: str | None = None
    password_policy_note: str | None = None


class RoutePermissionItem(BaseModel):
    method: str
    route: str
    allowed_roles: list[str]
    ownership_rule: str


class RolePermissionMatrixRead(BaseModel):
    total_routes: int
    routes: list[RoutePermissionItem]
