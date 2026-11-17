"""Tests for Web UX layer (/ui)."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_redirects_to_docs():
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/docs"


def test_ui_page_returns_html():
    response = client.get("/ui")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "LedgerForge" in response.text
    assert "Authentication" in response.text
    assert "Run Payroll" in response.text
    assert "View &amp; Download Payslip" in response.text or "View & Download Payslip" in response.text
