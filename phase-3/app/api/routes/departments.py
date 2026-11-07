"""HTTP route endpoints for departments with JWT & RBAC protection (LF-13)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.department import DepartmentResponse
from app.schemas.employee import EmployeeResponse
from app.services import department_service

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentResponse], summary="List all departments")
def list_departments(
    include_inactive: bool = Query(False, description="Include deactivated departments"),
    _current_user: User = Depends(require_role("ADMIN", "HR", "EMPLOYEE")),
    db: Session = Depends(get_db),
) -> list[DepartmentResponse]:
    return department_service.list_departments(db, include_inactive=include_inactive)


@router.get(
    "/{department_id}/employees",
    response_model=list[EmployeeResponse],
    summary="List all employees in a department",
)
def list_department_employees(
    department_id: str,
    include_inactive: bool = Query(False, description="Include inactive employees"),
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
) -> list[EmployeeResponse]:
    return department_service.get_department_employees(
        db, department_id=department_id, include_inactive=include_inactive
    )
