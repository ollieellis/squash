import pytest
from fastapi.testclient import TestClient
from main import app

def test_create_session():
    with TestClient(app) as client:
        response = client.post("/sessions/create", data={
            "date": "2026-05-04",
            "start_time": "08:00",
            "duration_minutes": "60",
            "num_courts": "1"
        }, follow_redirects=True)
        assert response.status_code == 200
