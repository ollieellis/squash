import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_nav_links_exist(client):
    response = client.get("/profiles/")
    assert response.status_code == 200
    assert 'href="/matches/"' in response.text
    assert 'href="/sessions/"' in response.text

def test_matches_route_exists(client):
    response = client.get("/matches/")
    # This might fail if the route isn't implemented, which is expected
    assert response.status_code == 200
