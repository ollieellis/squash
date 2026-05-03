import re
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from database import connect_to_mongo, close_mongo_connection, get_db
from models import Profile, Match
from elo import calculate_squash_elo
from contextlib import asynccontextmanager
from bson import ObjectId

@asynccontextmanager
async def lifespan(app: FastAPI):
    connect_to_mongo()
    yield
    close_mongo_connection()

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# ... (other routes remain same)

@app.get("/profiles/{profile_id}")
async def read_profile(profile_id: str, request: Request):
    db = await get_db()
    try:
        doc = await db.profiles.find_one({"_id": ObjectId(profile_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid profile ID")
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = Profile(**{**doc, "id": str(doc["_id"])})
    matches_cursor = db.matches.find({"$or": [{"player1_id": profile_id}, {"player2_id": profile_id}]}).sort("created_at", -1)
    recent_matches = []
    async for m in matches_cursor:
        match_obj = Match(**{**m, "id": str(m["_id"])})
        opponent_id = match_obj.player2_id if match_obj.player1_id == profile_id else match_obj.player1_id
        try:
            opponent_doc = await db.profiles.find_one({"_id": ObjectId(opponent_id)})
        except Exception:
            opponent_doc = None
        opponent_name = f"{opponent_doc['first_name']} {opponent_doc['last_name']}" if opponent_doc else "Unknown"
        opponent_elo = opponent_doc.get("elo", 0) if opponent_doc else 0
        recent_matches.append({"match": match_obj, "opponent_id": opponent_id, "opponent_name": opponent_name, "opponent_elo": int(opponent_elo)})
    form_guide = []
    for entry in recent_matches[:5]:
        match = entry["match"]
        res = "D" if match.winner_id == "draw" else ("W" if match.winner_id == profile_id else "L")
        form_guide.append({"result": res, "match_id": match.id})
    return templates.TemplateResponse(request=request, name="profile.html", context={"profile": profile, "form_guide": form_guide, "recent_matches": recent_matches})

@app.post("/matches/")
async def log_match(request: Request):
    data = await request.form()
    p1_id = data.get("player1_id")
    p2_id = data.get("player2_id")
    try:
        p1_score = int(data.get("player1_score", 0))
        p2_score = int(data.get("player2_score", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid scores")
    if not p1_id or not p2_id:
        raise HTTPException(status_code=400, detail="Missing players")
    if p1_id == p2_id:
        raise HTTPException(status_code=400, detail="A player cannot play against themselves.")
    db = await get_db()
    try:
        p1 = await db.profiles.find_one({"_id": ObjectId(p1_id)})
        p2 = await db.profiles.find_one({"_id": ObjectId(p2_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid player IDs")
    if not p1 or not p2:
        raise HTTPException(status_code=404, detail="Player not found")
    # (Rest of logic follows)
    p1_won = p1_score > p2_score
    winner_id = p1_id if p1_score > p2_score else (p2_id if p2_score > p1_score else "draw")
    new_p1_elo, new_p2_elo, delta = calculate_squash_elo(p1["elo"], p2["elo"], p1_score, p2_score)
    await db.profiles.update_one({"_id": ObjectId(p1_id)}, {"$set": {"elo": new_p1_elo}})
    await db.profiles.update_one({"_id": ObjectId(p2_id)}, {"$set": {"elo": new_p2_elo}})
    match = Match(player1_id=p1_id, player2_id=p2_id, player1_score=p1_score, player2_score=p2_score, winner_id=winner_id, elo_change=delta)
    result = await db.matches.insert_one(match.model_dump(exclude={"id"}))
    return templates.TemplateResponse(request=request, name="match_success.html", context={"match_id": str(result.inserted_id), "p1_name": f"{p1['first_name']} {p1['last_name']}", "p2_name": f"{p2['first_name']} {p2['last_name']}", "delta": delta})
