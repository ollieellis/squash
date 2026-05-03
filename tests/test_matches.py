import pytest
from fastapi.testclient import TestClient
from main import app
from elo import calculate_squash_elo

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_elo_calculation():
    # Test that it returns integers
    new_p1, new_p2, delta = calculate_squash_elo(1200, 1200, 3, 0)
    assert isinstance(new_p1, int)
    assert isinstance(delta, int)

def test_log_match(client):
    # Create two players
    client.post("/profiles/", json={"first_name": "Alice", "last_name": "Tester", "elo": 1200})
    client.post("/profiles/", json={"first_name": "Bob", "last_name": "Tester", "elo": 1200})
    
    # List them to get their IDs
    r = client.get("/profiles/")
    import re
    ids = re.findall(r'/profiles/([a-z0-9]+)', r.text)
    assert len(ids) >= 2
    p1_id, p2_id = ids[0], ids[1]
    
    # Log a match
    response = client.post("/matches/", data={
        "player1_id": p1_id,
        "player2_id": p2_id,
        "player1_score": 3,
        "player2_score": 0
    })
    
    assert response.status_code == 200
    assert "Match Logged Successfully!" in response.text
