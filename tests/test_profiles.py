import pytest
from fastapi.testclient import TestClient
from main import app
from database import get_db

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_create_profile(client):
    response = client.post("/profiles/", json={"first_name": "Test", "last_name": "User", "elo": 1000})
    assert response.status_code == 200
    # The response is an HTML fragment for HTMX
    assert "Profile Created!" in response.text
    assert "Test User" in response.text
    assert "1000" in response.text

def test_list_profiles(client):
    # Ensure there's at least one profile
    client.post("/profiles/", json={"first_name": "List", "last_name": "Tester", "elo": 1200})
    
    response = client.get("/profiles/")
    assert response.status_code == 200
    assert "Squash Leaderboard" in response.text
    assert "List Tester" in response.text

def test_duplicate_profile(client):
    client.post("/profiles/", json={"first_name": "Unique", "last_name": "Player", "elo": 1200})
    response = client.post("/profiles/", json={"first_name": "Unique", "last_name": "Player", "elo": 1200})
    assert response.status_code == 409
