from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_necessities_prices():
    response = client.get("/api/v1/prices/necessities-price")
    assert response.status_code == 200
    assert isinstance(response.json(), list)