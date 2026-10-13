"""Business logic for health checks (kept out of the route on purpose)."""

from app.schemas.health import HealthResponse


def get_health() -> HealthResponse:
    """Report liveness of the API process.

    Task 2+ can extend this to also ping the database.
    """
    return HealthResponse(status="ok")
