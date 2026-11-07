"""HTTP route endpoints for employees."""

import math
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import PaginatedResponse
from app.schemas.employee import EmployeeCreate, EmployeeResponse, EmployeeUpdate
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED, summary="Create a new employee")
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
) -> EmployeeResponse:
    return employee_service.create_employee(db, payload)


@router.get("", response_model=PaginatedResponse[EmployeeResponse], summary="List employees with filters and search")
def list_employees(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    department: str | None = Query(None, description="Filter by department ID (e.g. D01)"),
    status: str | None = Query(None, description="Filter by employment status (e.g. Active, Resigned)"),
    q: str | None = Query(None, description="Search term in name, email, or employee ID"),
    include_inactive: bool = Query(False, description="Include soft-deleted inactive employees"),
    db: Session = Depends(get_db),
) -> PaginatedResponse[EmployeeResponse]:
    items, total = employee_service.list_employees(
        session=db,
        page=page,
        size=size,
        department=department,
        status=status,
        q=q,
        include_inactive=include_inactive,
    )
    pages = math.ceil(total / size) if size > 0 else 0
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/{employee_id}", response_model=EmployeeResponse, summary="Get employee details by ID")
def get_employee(
    employee_id: str,
    db: Session = Depends(get_db),
) -> EmployeeResponse:
    return employee_service.get_employee(db, employee_id)


@router.patch("/{employee_id}", response_model=EmployeeResponse, summary="Update employee fields")
def update_employee(
    employee_id: str,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
) -> EmployeeResponse:
    return employee_service.update_employee(db, employee_id, payload)


@router.delete("/{employee_id}", response_model=EmployeeResponse, summary="Soft delete employee")
def delete_employee(
    employee_id: str,
    db: Session = Depends(get_db),
) -> EmployeeResponse:
    return employee_service.delete_employee(db, employee_id)


@router.get("/{employee_id}/team", response_model=list[EmployeeResponse], summary="Get employee's direct reports")
def get_employee_team(
    employee_id: str,
    include_inactive: bool = Query(False, description="Include soft-deleted team members"),
    db: Session = Depends(get_db),
) -> list[EmployeeResponse]:
    return employee_service.get_direct_reports(db, employee_id, include_inactive=include_inactive)
