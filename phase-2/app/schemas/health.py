"""Request/response schemas for the health endpoint."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "ledgerforge"
    version: str = "0.1.0"
    checks: dict[str, str] = {"database": "ok", "redis": "ok", "worker": "ok"}
