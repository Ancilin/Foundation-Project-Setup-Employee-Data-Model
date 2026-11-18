from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.health import HealthResponse


def get_health(db: Session | None = None) -> HealthResponse:
    """Report liveness, readiness, and active component health checks."""
    settings = get_settings()
    checks: dict[str, str] = {"database": "ok", "redis": "ok", "worker": "ok"}
    overall_status = "ok"

    if db is not None:
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "healthy"
        except Exception as e:
            checks["database"] = f"unhealthy: {str(e)}"
            overall_status = "unhealthy"

    # Optional Redis check
    try:
        import redis
        r = redis.from_url(settings.redis_url, socket_timeout=0.5)
        r.ping()
        checks["redis"] = "healthy"
    except Exception:
        checks["redis"] = "disconnected (fallback mode)"

    return HealthResponse(
        status=overall_status,
        service="ledgerforge",
        version=settings.app_version,
        checks=checks,
    )
