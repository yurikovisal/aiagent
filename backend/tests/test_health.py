from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_shape():
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "MEZA AI"
    assert "status" in data
    assert "dependencies" in data
    assert "postgres" in data["dependencies"]
    assert "redis" in data["dependencies"]
    assert "minio" in data["dependencies"]


def test_chat_status_ready():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/chat/status")
    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["streaming"] is True
