import asyncio
import random
from datetime import datetime, timedelta
from bson import ObjectId
from database import connect_to_mongo, close_mongo_connection, get_db
from models import Session, Profile, Match, EloHistory
from auth import get_password_hash
from loguru import logger

async def seed():
    connect_to_mongo()
    db = await get_db()

    # 1. Clear targeted collections
    await db.profiles.drop()
    await db.sessions.drop()
    await db.matches.drop()
    await db.elo_history.drop()
    logger.info("Cleared old data.")

    # 2. Seed 5 Profiles
    password_hash = get_password_hash("password")
    profiles = [
        {"first_name": "Alice", "last_name": "Smith", "elo": 1250, "email": "alice@example.com", "password_hash": password_hash},
        {"first_name": "Bob", "last_name": "Jones", "elo": 1180, "email": "bob@example.com", "password_hash": password_hash},
        {"first_name": "Charlie", "last_name": "Brown", "elo": 1300, "email": "charlie@example.com", "password_hash": password_hash},
        {"first_name": "Diana", "last_name": "Prince", "elo": 1220, "email": "diana@example.com", "password_hash": password_hash},
        {"first_name": "Edward", "last_name": "Norton", "elo": 1100, "email": "edward@example.com", "password_hash": password_hash},
    ]
    p_ids = []
    for p in profiles:
        res = await db.profiles.insert_one(p)
        p_id = str(res.inserted_id)
        p_ids.append(p_id)
        # Initial Elo History
        await db.elo_history.insert_one(
            EloHistory(profile_id=p_id, elo_value=p["elo"]).model_dump(exclude={"id"})
        )
    logger.info(f"Seeded {len(p_ids)} players.")

    # 3. Seed 3 Sessions
    sessions = []
    for i in range(3):
        s = Session(
            start_date=datetime.utcnow() - timedelta(days=i*7),
            end_date=datetime.utcnow() - timedelta(days=i*7, hours=-1),
            location=f"Squash Court {i+1}",
            num_courts=2,
            max_players=6,
            player_ids=random.sample(p_ids, 4)
        )
        res = await db.sessions.insert_one(s.model_dump(exclude={"id"}))
        sessions.append(str(res.inserted_id))
    logger.info(f"Seeded 3 sessions.")

    # 4. Seed 15 Matches
    for _ in range(15):
        s_id = random.choice(sessions)
        p1_id, p2_id = random.sample(p_ids, 2)
        score1, score2 = random.sample([11, 9, 8, 12, 13, 7], 2)
        winner = p1_id if score1 > score2 else p2_id
        
        # Get current elos to record history (simplified for seeding)
        p1 = await db.profiles.find_one({"_id": ObjectId(p1_id)})
        p2 = await db.profiles.find_one({"_id": ObjectId(p2_id)})
        
        delta = random.uniform(5.0, 20.0)
        new_p1_elo = p1["elo"] + (delta if winner == p1_id else -delta)
        new_p2_elo = p2["elo"] + (delta if winner == p2_id else -delta)
        
        match = Match(
            player1_id=p1_id, player2_id=p2_id,
            player1_score=score1, player2_score=score2,
            winner_id=winner, elo_change=delta,
            session_id=s_id
        )
        res = await db.matches.insert_one(match.model_dump(exclude={"id"}))
        match_id = str(res.inserted_id)
        
        # Update Profiles
        await db.profiles.update_one({"_id": ObjectId(p1_id)}, {"$set": {"elo": new_p1_elo}})
        await db.profiles.update_one({"_id": ObjectId(p2_id)}, {"$set": {"elo": new_p2_elo}})
        
        # Record History
        await db.elo_history.insert_many([
            EloHistory(profile_id=p1_id, elo_value=new_p1_elo, match_id=match_id, session_id=s_id).model_dump(exclude={"id"}),
            EloHistory(profile_id=p2_id, elo_value=new_p2_elo, match_id=match_id, session_id=s_id).model_dump(exclude={"id"})
        ])
        
    logger.info("Seeded 15 sample matches.")

    close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(seed())

