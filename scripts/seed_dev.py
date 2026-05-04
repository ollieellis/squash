import asyncio
import asyncio
import random
from datetime import datetime, timedelta
from database import connect_to_mongo, close_mongo_connection, get_db
from models import Session, Profile, Match
from loguru import logger

async def seed():
    connect_to_mongo()
    db = await get_db()

    # 1. Clear targeted collections
    await db.profiles.drop()
    await db.sessions.drop()
    await db.matches.drop()
    logger.info("Cleared old data.")

    # 2. Seed 5 Profiles
    profiles = [
        {"first_name": "Alice", "last_name": "Smith", "elo": 1250},
        {"first_name": "Bob", "last_name": "Jones", "elo": 1180},
        {"first_name": "Charlie", "last_name": "Brown", "elo": 1300},
        {"first_name": "Diana", "last_name": "Prince", "elo": 1220},
        {"first_name": "Edward", "last_name": "Norton", "elo": 1100},
    ]
    p_ids = []
    for p in profiles:
        res = await db.profiles.insert_one(p)
        p_ids.append(str(res.inserted_id))
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
        p1, p2 = random.sample(p_ids, 2)
        score1, score2 = random.sample([11, 9, 8, 12, 13, 7], 2)
        winner = p1 if score1 > score2 else p2
        match = Match(
            player1_id=p1, player2_id=p2,
            player1_score=score1, player2_score=score2,
            winner_id=winner, elo_change=random.uniform(5.0, 20.0),
            session_id=s_id
        )
        await db.matches.insert_one(match.model_dump(exclude={"id"}))
    logger.info("Seeded 15 sample matches.")

    close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(seed())

