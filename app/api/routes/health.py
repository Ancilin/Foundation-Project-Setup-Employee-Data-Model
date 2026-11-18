"""HTTP layer: parse the request, call a service, return a schema."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.health import HealthResponse
from app.services import health_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness and database health check")
def health(response: Response, db: Session = Depends(get_db)) -> HealthResponse:
    res = health_service.get_health(db=db)
    if res.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return res
