from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_greet():
    response = client.get("/greet")
    assert response.status_code == 200
    assert "message" in response.json()
