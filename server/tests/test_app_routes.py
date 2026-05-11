from fastapi.testclient import TestClient

from app.main import app


def test_root_returns_service_info():
    response = TestClient(app).get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "running"
    assert body["data"]["health_url"] == "/api/health"


def test_api_root_returns_endpoint_info():
    response = TestClient(app).get("/api")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["auth_url"] == "/api/auth"

