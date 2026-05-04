import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_session_modal_inputs(client):
    response = client.get("/sessions/")
    assert response.status_code == 200
    assert 'name="date"' in response.text
    assert 'type="date"' in response.text
