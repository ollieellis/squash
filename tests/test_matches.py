import pytest
from fastapi.testclient import TestClient
from squash.main import app
from squash.elo import calculate_squash_elo
from bson import ObjectId

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
    email1 = f"alice_{ObjectId()}@test.com"
    email2 = f"bob_{ObjectId()}@test.com"
    # Register two players
    client.post("/register", data={"first_name": "Alice", "last_name": "Tester", "email": email1, "password": "password123"})
    client.post("/register", data={"first_name": "Bob", "last_name": "Tester", "email": email2, "password": "password123"})
    
    # Explicitly login as Bob to be sure
    client.post("/login", data={"email": email2, "password": "password123"})
    
    # List them to get their IDs
    r = client.get("/profiles/")
    import re
    # Extract unique IDs from the page to avoid duplicates (e.g. from navbar and table)
    ids = list(dict.fromkeys(re.findall(r'/profiles/([a-f0-9]{24})', r.text)))
    assert len(ids) >= 2
    p1_id, p2_id = ids[0], ids[1]
    
    # Log a match as Bob
    response = client.post("/matches/", data={
        "player1_id": p1_id,
        "player2_id": p2_id,
        "player1_score": 3,
        "player2_score": 0
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert "Match Logged Successfully!" in response.text or "ELO Delta" in response.text
