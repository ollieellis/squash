from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")

class Database:
    client: AsyncIOMotorClient = None

db = Database()

async def get_db():
    return db.client.squash_db

def connect_to_mongo():
    db.client = AsyncIOMotorClient(MONGO_URL)

def close_mongo_connection():
    db.client.close()
