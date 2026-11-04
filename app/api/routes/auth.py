"""Authentication & Role-Based Access Control HTTP routes (LF-13):
- POST /auth/login (accepts either JSON body or OAuth2 form data for Swagger UI Authorize button)
- GET /auth/me
- GET /auth/permissions
- GET /auth/users
- PATCH /auth/users/{user_id}/deactivate
- PATCH /auth/users/{user_id}/activate
"""

from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RolePermissionMatrixRead,
    TokenResponse,
    UserRead,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth & RBAC"])


@router.post(
    "/login",
    response_model=TokenResponse,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": LoginRequest.model_json_schema(),
                    "example": {
                        "username": "sanjay.kumar@znova-demo.example",
                        "password": "DemoPass@123",
                    },
                },
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string", "example": "sanjay.kumar@znova-demo.example"},
                            "password": {"type": "string", "example": "DemoPass@123"},
                        },
                        "required": ["username", "password"],
                    }
                },
            },
            "required": True,
        }
    },
)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate with username (email, user_id, or employee_id) and password.
    Returns a JWT access token valid for 30 minutes.
    Supports both JSON payloads and OAuth2 form data (Swagger UI Authorize button).
    """
    username: str | None = None
    password: str | None = None

    content_type = request.headers.get("content-type", "").lower()
    raw_bytes = await request.body()
    raw_text = raw_bytes.decode("utf-8", errors="ignore").strip()

    if "application/json" in content_type or raw_text.startswith("{"):
        try:
            body = await request.json()
            if isinstance(body, dict):
                username = str(body.get("username") or "").strip()
                password = str(body.get("password") or "")
        except Exception:
            pass
    elif raw_text:
        parsed = parse_qs(raw_text, keep_blank_values=True)
        username = (parsed.get("username", [""])[0] or "").strip()
        password = parsed.get("password", [""])[0] or ""

    if not username or not password:
        raise UnauthorizedError("Username and password are required.", error_code="INVALID_CREDENTIALS")

    return auth_service.authenticate_user(session=db, username_or_id=username, password=password)


@router.get("/me", response_model=UserRead)
def get_my_profile(
    current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
):
    """Return the authenticated user's profile (excludes password_hash)."""
    return current_user


@router.get("/permissions", response_model=RolePermissionMatrixRead)
def get_permissions_table(
    _current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
):
    """Return the role-based access control matrix listing which role may use each route."""
    return auth_service.get_role_permissions_matrix()


@router.get("/users", response_model=list[UserRead])
def get_users(
    role: str | None = Query(default=None, description="Filter by role: ADMIN, HR, EMPLOYEE"),
    is_active: str | None = Query(default=None, description="Filter by active flag: Y or N"),
    _current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """List users (Admin only)."""
    return auth_service.list_users(db, role=role, is_active=is_active)


@router.patch("/users/{user_id}/deactivate", response_model=UserRead)
def deactivate_user_account(
    user_id: str,
    _current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Deactivate a user account (Admin only). Any valid JWT held by the user is immediately rejected on subsequent calls."""
    return auth_service.set_user_active_status(db, user_id=user_id, active=False)


@router.patch("/users/{user_id}/activate", response_model=UserRead)
def activate_user_account(
    user_id: str,
    _current_user: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    """Reactivate a user account (Admin only)."""
    return auth_service.set_user_active_status(db, user_id=user_id, active=True)
