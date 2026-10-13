"""Request/response schemas for the health endpoint."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
