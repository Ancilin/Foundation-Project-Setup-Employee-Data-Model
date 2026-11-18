"""Tests for health endpoint, verifying liveness, readiness, and database failure detection."""

from unittest.mock import MagicMock
from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ledgerforge"
    assert data["checks"]["database"] in ("healthy", "ok")


def test_api_v1_health_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "ledgerforge"


def test_docs_page_is_available(client):
    assert client.get("/docs").status_code == 200


def test_health_detects_database_failure(client):
    """When the database connection fails, /health must return 503 and report unhealthy status."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = OperationalError("connection refused", {}, None)

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "unhealthy" in data["checks"]["database"]
    finally:
        app.dependency_overrides.pop(get_db, None)
