import pytest
from fastapi.testclient import TestClient
from main import app
from elo import calculate_elo_change, get_new_elos

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_elo_calculation():
    # Equal players
    change = calculate_elo_change(1200, 1200, True)
    assert change == 16 # K=32, expected 0.5, actual 1.0 -> 32 * 0.5 = 16
    
    # Strong player wins against weak player
    change = calculate_elo_change(2000, 1000, True)
    assert change < 5 # Should be very small
    
    # Weak player wins against strong player
    change = calculate_elo_change(1000, 2000, True)
    assert change > 25 # Should be very large

def test_log_match(client):
    # Create two players
    p1 = client.post("/profiles/", json={"first_name": "Player", "last_name": "One", "elo": 1200})
    p2 = client.post("/profiles/", json={"first_name": "Player", "last_name": "Two", "elo": 1200})
    
    import re
    p1_id = re.search(r"/profiles/([0-9a-f-]+)", p1.text).group(1)
    p2_id = re.search(r"/profiles/([0-9a-f-]+)", p2.text).group(1)
    
    # Log a match where p1 wins 3-0
    response = client.post("/matches/", data={
        "player1_id": p1_id,
        "player2_id": p2_id,
        "player1_score": 3,
        "player2_score": 0
    })
    
    assert response.status_code == 200
    assert "Match Logged Successfully!" in response.text
    assert "16" in response.text # Standard change for equal players

    # Verify ELO updated in profiles
    p1_profile = client.get(f"/profiles/{p1_id}")
    assert "1216" in p1_profile.text
    
    p2_profile = client.get(f"/profiles/{p2_id}")
    assert "1184" in p2_profile.text
