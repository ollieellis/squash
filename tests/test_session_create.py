import pytest
from fastapi.testclient import TestClient
from squash.main import app

def test_create_session():
    with TestClient(app) as client:
        # Register
        client.post("/register", data={"first_name": "S", "last_name": "T", "email": "session@test.com", "password": "pass"})
        # Explicit Login
        client.post("/login", data={"email": "session@test.com", "password": "pass"})
        
        response = client.post("/sessions/create", data={
            "date": "2026-05-04",
            "start_time": "08:00",
            "duration_minutes": "60",
            "num_courts": "1"
        }, follow_redirects=True)
        assert response.status_code == 200
        assert "2026-05-04 08:00" in response.text
