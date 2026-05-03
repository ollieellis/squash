from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from database import connect_to_mongo, close_mongo_connection, get_db
from models import Profile, Match
from elo import get_new_elos
from contextlib import asynccontextmanager
from bson import ObjectId

@asynccontextmanager
async def lifespan(app: FastAPI):
    connect_to_mongo()
    yield
    close_mongo_connection()

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def root(request: Request):
    db = await get_db()
    profiles_cursor = db.profiles.find().sort("first_name", 1)
    profiles = [Profile(**{**doc, "id": str(doc["_id"])}) async for doc in profiles_cursor]
    return templates.TemplateResponse(request=request, name="index.html", context={
        "message": "Welcome to Squash ELO (MongoDB)",
        "profiles": profiles
    })

@app.get("/profiles/")
async def list_profiles(request: Request):
    db = await get_db()
    profiles_cursor = db.profiles.find().sort("elo", -1)
    profiles = [Profile(**{**doc, "id": str(doc["_id"])}) async for doc in profiles_cursor]
    return templates.TemplateResponse(request=request, name="profiles.html", context={"profiles": profiles})

@app.get("/profiles/{profile_id}")
async def read_profile(profile_id: str, request: Request):
    db = await get_db()
    doc = await db.profiles.find_one({"_id": ObjectId(profile_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = Profile(**{**doc, "id": str(doc["_id"])})

    matches_cursor = db.matches.find({"$or": [{"player1_id": profile_id}, {"player2_id": profile_id}]}).sort("created_at", -1)
    player_matches = [Match(**{**m, "id": str(m["_id"])}) async for m in matches_cursor]

    form_guide = []
    for match in player_matches[:5]:
        res = "D" if match.winner_id == "draw" else ("W" if match.winner_id == profile_id else "L")
        form_guide.append({"result": res, "match_id": match.id})

    return templates.TemplateResponse(request=request, name="profile.html", context={
        "profile": profile, 
        "form_guide": form_guide,
        "recent_matches": player_matches
    })

@app.post("/profiles/")
async def create_profile(request: Request):
    data = await request.json()
    profile = Profile(**data)
    db = await get_db()
    
    # Check for existing profile
    existing = await db.profiles.find_one({
        "first_name": profile.first_name,
        "last_name": profile.last_name
    })
    
    if existing:
        raise HTTPException(status_code=409, detail="Profile already exists")
    
    profile_dict = profile.model_dump(exclude={"id"})
    result = await db.profiles.insert_one(profile_dict)
    profile.id = str(result.inserted_id)
    return templates.TemplateResponse(request=request, name="profile_snippet.html", context={"profile": profile})

@app.post("/matches/")
async def log_match(request: Request):
    data = await request.form()
    p1_id = data.get("player1_id")
    p2_id = data.get("player2_id")
    p1_score = int(data.get("player1_score"))
    p2_score = int(data.get("player2_score"))
    
    if p1_id == p2_id:
        raise HTTPException(status_code=400, detail="A player cannot play against themselves.")
    
    db = await get_db()
    p1 = await db.profiles.find_one({"_id": ObjectId(p1_id)})
    p2 = await db.profiles.find_one({"_id": ObjectId(p2_id)})
    
    if not p1 or not p2:
        raise HTTPException(status_code=404, detail="Player not found")
    
    p1_won = p1_score > p2_score
    winner_id = p1_id if p1_score > p2_score else (p2_id if p2_score > p1_score else "draw")
    
    new_p1_elo, new_p2_elo, delta = get_new_elos(p1["elo"], p2["elo"], p1_won)
    
    await db.profiles.update_one({"_id": ObjectId(p1_id)}, {"$set": {"elo": new_p1_elo}})
    await db.profiles.update_one({"_id": ObjectId(p2_id)}, {"$set": {"elo": new_p2_elo}})
    
    match = Match(
        player1_id=p1_id,
        player2_id=p2_id,
        player1_score=p1_score,
        player2_score=p2_score,
        winner_id=winner_id,
        elo_change=delta
    )
    
    result = await db.matches.insert_one(match.model_dump(exclude={"id"}))
    
    return templates.TemplateResponse(request=request, name="match_success.html", context={
        "match_id": str(result.inserted_id),
        "p1_name": f"{p1['first_name']} {p1['last_name']}",
        "p2_name": f"{p2['first_name']} {p2['last_name']}",
        "delta": delta
    })

@app.get("/matches/{match_id}")
async def read_match(match_id: str, request: Request):
    db = await get_db()
    match = await db.matches.find_one({"_id": ObjectId(match_id)})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    p1 = await db.profiles.find_one({"_id": ObjectId(match["player1_id"])})
    p2 = await db.profiles.find_one({"_id": ObjectId(match["player2_id"])})
    
    return templates.TemplateResponse(request=request, name="match.html", context={
        "match": match,
        "p1_name": f"{p1['first_name']} {p1['last_name']}",
        "p2_name": f"{p2['first_name']} {p2['last_name']}"
    })
