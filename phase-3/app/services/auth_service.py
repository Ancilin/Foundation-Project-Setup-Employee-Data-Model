"""Authentication and User Management service (LF-13):
- Login with bcrypt password verification and 30-minute JWT issuance
- User activation / deactivation (revokes active token access immediately on next request)
- Complete Role-Based Access Control (RBAC) route matrix
"""

from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    verify_password,
)
from app.models.user import User

ROLE_PERMISSION_TABLE: list[dict[str, Any]] = [
    {"method": "GET", "route": "/health", "allowed_roles": ["PUBLIC"], "ownership_rule": "Public health check"},
    {"method": "POST", "route": "/auth/login", "allowed_roles": ["PUBLIC"], "ownership_rule": "Public login endpoint (returns 30-min JWT)"},
    {"method": "GET", "route": "/auth/me", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "Authenticated user's own profile"},
    {"method": "GET", "route": "/auth/permissions", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "View role-permission table"},
    {"method": "GET", "route": "/auth/users", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only"},
    {"method": "PATCH", "route": "/auth/users/{user_id}/deactivate", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only (immediately blocks token)"},
    {"method": "PATCH", "route": "/auth/users/{user_id}/activate", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only"},
    {"method": "POST", "route": "/employees", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/employees", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/employees/{employee_id}", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "EMPLOYEE may read only their own employee_id"},
    {"method": "PATCH", "route": "/employees/{employee_id}", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "DELETE", "route": "/employees/{employee_id}", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only"},
    {"method": "GET", "route": "/employees/{employee_id}/team", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "EMPLOYEE may read only their own direct reports"},
    {"method": "GET", "route": "/departments", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "All authenticated users"},
    {"method": "GET", "route": "/departments/{department_id}/employees", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/attendance", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/attendance/{employee_id}", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "EMPLOYEE may read only their own attendance"},
    {"method": "GET", "route": "/attendance/{employee_id}/summary", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "EMPLOYEE may read only their own summary"},
    {"method": "GET", "route": "/attendance/{employee_id}/summary/{month}", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "EMPLOYEE may read only their own summary"},
    {"method": "GET", "route": "/leave/holidays", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "All authenticated users"},
    {"method": "GET", "route": "/leave/types", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "All authenticated users"},
    {"method": "GET", "route": "/leave/balances/{employee_id}", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "EMPLOYEE may read only their own leave balance"},
    {"method": "GET", "route": "/leave/requests", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "EMPLOYEE sees only their own leave requests"},
    {"method": "POST", "route": "/leave/requests", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "EMPLOYEE may apply only for their own employee_id"},
    {"method": "POST", "route": "/leave/requests/{leave_request_id}/approve", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/leave/requests/{leave_request_id}/reject", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/payroll/calculate", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/payroll/runs", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/payroll/runs", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/payroll/runs/reconciliation", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/payroll/runs/{run_id}", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/payroll/runs/{run_id}/process", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/payroll/runs/{run_id}/approve", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only (separation of duties)"},
    {"method": "POST", "route": "/payroll/runs/{run_id}/pay", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only"},
    {"method": "POST", "route": "/payroll/runs/{run_id}/reverse", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only"},
    {"method": "GET", "route": "/payslips/{employee_id}/{run_id}", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "EMPLOYEE may read only their own payslip"},
    {"method": "GET", "route": "/payslips/{employee_id}/{run_id}/pdf", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "EMPLOYEE may download only their own payslip PDF"},
    {"method": "GET", "route": "/ledger/accounts", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/ledger/accounts/{account_code}/balance", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/ledger/entries", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only"},
    {"method": "GET", "route": "/ledger/entries/{entry_id}", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "PATCH", "route": "/ledger/entries/{entry_id}", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only"},
    {"method": "DELETE", "route": "/ledger/entries/{entry_id}", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only"},
    {"method": "POST", "route": "/ledger/entries/{entry_id}/reverse", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only"},
    {"method": "POST", "route": "/ledger/payroll/{run_id}/post", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/invoices/clients", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/invoices/receivables", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/invoices", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/invoices/{invoice_id}", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/invoices/{invoice_id}/send", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/invoices/{invoice_id}/post", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/invoices/{invoice_id}/payments", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/invoices/{invoice_id}/overdue", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/invoices/{invoice_id}/cancel", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only"},
    {"method": "GET", "route": "/expenses/vendors", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "All authenticated users"},
    {"method": "GET", "route": "/expenses/report", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/expenses/reconciliation/monthly", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/expenses/duplicates", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/expenses/duplicates/check", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/expenses", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "POST", "route": "/expenses", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "EMPLOYEE may submit only for their own employee_id"},
    {"method": "GET", "route": "/expenses/{expense_id}", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "EMPLOYEE may view only bills they submitted"},
    {"method": "POST", "route": "/expenses/{expense_id}/approve", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only (separation of duties)"},
    {"method": "POST", "route": "/expenses/{expense_id}/pay", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only"},
    {"method": "GET", "route": "/tax/slabs", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "All authenticated users"},
    {"method": "POST", "route": "/tax/slabs", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only (change tax rules)"},
    {"method": "PATCH", "route": "/tax/slabs/{slab_id}", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only (change tax rules)"},
    {"method": "GET", "route": "/tax/parameters", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "All authenticated users"},
    {"method": "PATCH", "route": "/tax/parameters/{parameter}", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only (change tax rules)"},
    {"method": "GET", "route": "/tax/statutory-rates", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "All authenticated users"},
    {"method": "PATCH", "route": "/tax/statutory-rates/{parameter}", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only (change statutory rules)"},
    {"method": "GET", "route": "/tax/breakdown/{employee_id}/{month}", "allowed_roles": ["ADMIN", "HR", "EMPLOYEE"], "ownership_rule": "EMPLOYEE may view only their own tax breakdown"},
    {"method": "POST", "route": "/tax/slabs/rerun-demo", "allowed_roles": ["ADMIN"], "ownership_rule": "Admin only"},
    {"method": "GET", "route": "/tax/reports/pf", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/tax/reports/esi", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/tax/reports/tds", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/tax/reports/summary", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/reports/trial-balance", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/reports/profit-and-loss", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
    {"method": "GET", "route": "/reports/balance-sheet", "allowed_roles": ["ADMIN", "HR"], "ownership_rule": "HR and Admin only"},
]


def authenticate_user(
    session: Session,
    username_or_id: str,
    password: str,
) -> dict[str, Any]:
    """Authenticate a user by username (email), user_id, or employee_id and verify their bcrypt password hash.
    Refuses inactive/deactivated accounts and returns a 30-minute JWT access token.
    """
    ident = (username_or_id or "").strip()
    if not ident or not password:
        raise UnauthorizedError("Username and password are required.", error_code="INVALID_CREDENTIALS")

    user = session.scalar(
        select(User).where(
            or_(
                User.username == ident,
                User.user_id == ident,
                User.employee_id == ident,
            )
        )
    )
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError(
            "Invalid username or password.",
            error_code="INVALID_CREDENTIALS",
        )

    if str(user.is_active).strip().upper() != "Y":
        raise UnauthorizedError(
            f"User account '{user.username}' ({user.user_id}) is deactivated.",
            error_code="USER_DEACTIVATED",
        )

    user.last_login_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session.commit()

    token = create_access_token(
        user_id=user.user_id,
        username=user.username,
        role=user.role,
        employee_id=user.employee_id,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user_id": user.user_id,
        "employee_id": user.employee_id,
        "username": user.username,
        "role": user.role,
    }


def list_users(
    session: Session,
    role: str | None = None,
    is_active: str | None = None,
) -> list[User]:
    """List users with optional role and active-status filters."""
    stmt = select(User).order_by(User.user_id)
    if role:
        stmt = stmt.where(User.role == role.strip().upper())
    if is_active:
        stmt = stmt.where(User.is_active == is_active.strip().upper())
    return list(session.scalars(stmt).all())


def set_user_active_status(
    session: Session,
    user_id: str,
    active: bool,
) -> User:
    """Activate or deactivate a user account.
    Deactivating a user immediately invalidates any active JWT token they hold on subsequent requests.
    """
    user = session.get(User, user_id)
    if not user:
        raise NotFoundError(f"User '{user_id}' not found")
    user.is_active = "Y" if active else "N"
    session.commit()
    session.refresh(user)
    return user


def get_role_permissions_matrix() -> dict[str, Any]:
    return {
        "total_routes": len(ROLE_PERMISSION_TABLE),
        "routes": ROLE_PERMISSION_TABLE,
    }
