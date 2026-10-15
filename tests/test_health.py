def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "ledgerforge"


def test_api_v1_health_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "ledgerforge"


def test_docs_page_is_available(client):
    assert client.get("/docs").status_code == 200
