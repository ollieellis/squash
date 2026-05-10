import pytest
from fastapi.testclient import TestClient
from squash.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_session_modal_inputs(client):
    # Register
    client.post("/register", data={"first_name": "U", "last_name": "I", "email": "ui@test.com", "password": "pass"})
    # Explicit Login
    client.post("/login", data={"email": "ui@test.com", "password": "pass"})
    
    response = client.get("/sessions/")
    assert response.status_code == 200
    assert 'name="date"' in response.text
    assert 'type="date"' in response.text
