import pytest
from fastapi.testclient import TestClient
from squash.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_nonexistent_profile(client):
    response = client.get("/profiles/nonexistentid")
    assert response.status_code == 404

def test_invalid_match_log(client):
    # Register and login
    client.post("/register", data={"first_name": "R", "last_name": "T", "email": "robust@test.com", "password": "pass"})
    client.post("/login", data={"email": "robust@test.com", "password": "pass"})
    
    # Missing form fields
    response = client.post("/matches/", data={"player1_score": "3"})
    # The app explicitly returns 400 for missing players
    assert response.status_code == 400

def test_self_play_match(client):
    # Register and login
    client.post("/register", data={"first_name": "R2", "last_name": "T2", "email": "robust2@test.com", "password": "pass"})
    client.post("/login", data={"email": "robust2@test.com", "password": "pass"})
    
    # Log a match where player1 == player2
    response = client.post("/matches/", data={
        "player1_id": "123",
        "player2_id": "123",
        "player1_score": "3",
        "player2_score": "0"
    })
    assert response.status_code == 400

