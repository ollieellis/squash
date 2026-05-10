import pytest
from fastapi.testclient import TestClient
from squash.main import app
from squash.database import get_db
from bson import ObjectId

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_create_profile(client):
    email = f"test_{ObjectId()}@user.com"
    # Registration
    client.post("/register", data={"first_name": "Test", "last_name": "User", "email": email, "password": "password123"})
    
    # Explicit login
    client.post("/login", data={"email": email, "password": "password123"})
    
    # Check leaderboard
    response = client.get("/profiles/")
    assert response.status_code == 200
    assert "Leaderboard" in response.text
    assert "Test User" in response.text

def test_list_profiles(client):
    email = f"list_{ObjectId()}@tester.com"
    # Register a user so they appear on leaderboard
    client.post("/register", data={"first_name": "List", "last_name": "Tester", "email": email, "password": "password123"})
    
    response = client.get("/profiles/")
    assert response.status_code == 200
    assert "Leaderboard" in response.text
    assert "List Tester" in response.text

def test_duplicate_profile(client):
    email = f"unique_{ObjectId()}@player.com"
    client.post("/register", data={"first_name": "Unique", "last_name": "Player", "email": email, "password": "password123"})
    response = client.post("/register", data={"first_name": "Unique", "last_name": "Player", "email": email, "password": "password123"})
    # Registration returns a 200 with an error message in HTML context
    assert response.status_code == 200
    assert "Email already registered" in response.text
