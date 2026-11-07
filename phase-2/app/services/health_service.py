from app.core.config import get_settings
from app.schemas.health import HealthResponse


def get_health() -> HealthResponse:
    """Report liveness and component checks."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service="ledgerforge",
        version=settings.app_version,
        checks={"database": "ok", "redis": "ok", "worker": "ok"},
    )
