from database import connect_to_mongo, close_mongo_connection, get_db
import asyncio
from loguru import logger

async def drop_targeted():
    connect_to_mongo()
    db = await get_db()
    
    target_collections = {"profiles", "sessions", "matches"}
    existing = await db.list_collection_names()
    
    for col in existing:
        if col in target_collections:
            await db.drop_collection(col)
            logger.info(f"Dropped targeted collection: {col}")
        else:
            logger.warning(f"Skipped outstanding collection: {col}")
            
    close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(drop_targeted())
