"""Collects all route modules."""

from fastapi import APIRouter

from app.api.routes import departments, employees, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(departments.router)
api_router.include_router(employees.router)
