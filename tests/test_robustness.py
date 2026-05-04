import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_nonexistent_profile(client):
    response = client.get("/profiles/nonexistentid")
    assert response.status_code == 404

def test_invalid_match_log(client):
    # Missing form fields
    response = client.post("/matches/", data={"player1_score": "3"})
    # Should either be a 400 or a 422
    assert response.status_code in [400, 422]

def test_self_play_match(client):
    # Log a match where player1 == player2
    response = client.post("/matches/", data={
        "player1_id": "123",
        "player2_id": "123",
        "player1_score": "3",
        "player2_score": "0"
    })
    assert response.status_code == 400
