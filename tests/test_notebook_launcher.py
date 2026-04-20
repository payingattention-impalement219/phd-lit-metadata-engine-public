from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_source_status_endpoint_lists_sources():
    client = TestClient(app)
    response = client.get("/api/sources/status")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert "pubmed" in names
    assert "scopus" in names

