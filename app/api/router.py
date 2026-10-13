"""Collects all route modules. Later tasks add their routers here."""

from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter()
api_router.include_router(health.router)
