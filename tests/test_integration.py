import pytest
from fastapi.testclient import TestClient
from main import app
import asyncio
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")

@pytest.fixture(scope="module")
def client():
    # TestClient as context manager triggers the FastAPI lifespan (connect_to_mongo)
    with TestClient(app) as c:
        yield c

async def get_test_db_client():
    client = AsyncIOMotorClient(MONGO_URL)
    return client, client.squash_db

def test_auth_and_elo_history_flow(client):
    # 1. Register two users
    user1_email = "tester1@example.com"
    user2_email = "tester2@example.com"
    
    async def cleanup():
        c, db = await get_test_db_client()
        await db.profiles.delete_many({"email": {"$in": [user1_email, user2_email]}})
        c.close()
    
    asyncio.run(cleanup())

    # Register User 1
    resp1 = client.post("/register", data={
        "first_name": "Tester", "last_name": "One",
        "email": user1_email, "password": "password123"
    }, follow_redirects=True)
    assert resp1.status_code == 200
    assert "My Profile" in resp1.text

    # Register User 2
    resp2 = client.post("/register", data={
        "first_name": "Tester", "last_name": "Two",
        "email": user2_email, "password": "password123"
    }, follow_redirects=True)
    assert resp2.status_code == 200

    # Get their IDs from the database
    async def get_user_ids():
        c, db = await get_test_db_client()
        u1 = await db.profiles.find_one({"email": user1_email})
        u2 = await db.profiles.find_one({"email": user2_email})
        c.close()
        return str(u1["_id"]), str(u2["_id"])
    
    u1_id, u2_id = asyncio.run(get_user_ids())

    # 2. Log a match
    match_resp = client.post("/matches/", data={
        "player1_id": u1_id,
        "player2_id": u2_id,
        "player1_score": 3,
        "player2_score": 1
    }, follow_redirects=True)
    
    assert match_resp.status_code == 200
    assert "Match Logged Successfully!" in match_resp.text

    # 3. Verify ELO History in DB
    async def verify_history():
        c, db = await get_test_db_client()
        h1 = await db.elo_history.find({"profile_id": u1_id}).to_list(length=10)
        h2 = await db.elo_history.find({"profile_id": u2_id}).to_list(length=10)
        
        # 1 Initial + 1 Match = 2
        assert len(h1) == 2
        assert len(h2) == 2
        
        match_entry = next(e for e in h1 if e.get("match_id"))
        assert match_entry["match_id"] is not None
        
        prof1 = await db.profiles.find_one({"_id": ObjectId(u1_id)})
        assert prof1["elo"] > 1200
        assert prof1["elo"] == match_entry["elo_value"]
        c.close()

    asyncio.run(verify_history())
