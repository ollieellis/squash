from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from database import connect_to_mongo, close_mongo_connection, get_db
from models import Profile, Match, Session
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

@app.post("/profiles/")
async def create_profile(request: Request):
    data = await request.json()
    profile = Profile(**data)
    db = await get_db()
    existing = await db.profiles.find_one({"first_name": profile.first_name, "last_name": profile.last_name})
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
    try:
        p1_score = int(data.get("player1_score", 0))
        p2_score = int(data.get("player2_score", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid scores")
    if not p1_id or not p2_id or p1_id == p2_id:
        raise HTTPException(status_code=400, detail="Invalid players")
    
    db = await get_db()
    try:
        p1 = await db.profiles.find_one({"_id": ObjectId(p1_id)})
        p2 = await db.profiles.find_one({"_id": ObjectId(p2_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid player IDs")
    if not p1 or not p2:
        raise HTTPException(status_code=404, detail="Player not found")
        
    p1_won = p1_score > p2_score
    winner_id = p1_id if p1_score > p2_score else (p2_id if p2_score > p1_score else "draw")
    new_p1_elo, new_p2_elo, delta = calculate_squash_elo(p1["elo"], p2["elo"], p1_score, p2_score)
    await db.profiles.update_one({"_id": ObjectId(p1_id)}, {"$set": {"elo": new_p1_elo}})
    await db.profiles.update_one({"_id": ObjectId(p2_id)}, {"$set": {"elo": new_p2_elo}})
    
    match = Match(
        player1_id=p1_id, 
        player2_id=p2_id, 
        player1_score=p1_score, 
        player2_score=p2_score, 
        winner_id=winner_id, 
        elo_change=delta,
        session_id=data.get("session_id") or None
    )
    result = await db.matches.insert_one(match.model_dump(exclude={"id"}))
    
    return templates.TemplateResponse(request=request, name="match_success.html", context={
        "match_id": str(result.inserted_id), "p1_name": f"{p1['first_name']} {p1['last_name']}",
        "p2_name": f"{p2['first_name']} {p2['last_name']}", "delta": delta
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
        "match": match, "p1_name": f"{p1['first_name']} {p1['last_name']}",
        "p2_name": f"{p2['first_name']} {p2['last_name']}"
    })

@app.get("/matches/")
async def list_matches(request: Request):
    db = await get_db()
    cursor = db.matches.find().sort("created_at", -1)
    matches = [Match(**{**m, "id": str(m["_id"])}) async for m in cursor]
    enriched = []
    for m in matches:
        p1 = await db.profiles.find_one({"_id": ObjectId(m.player1_id)})
        p2 = await db.profiles.find_one({"_id": ObjectId(m.player2_id)})
        enriched.append({
            "match": m,
            "p1_name": f"{p1['first_name']} {p1['last_name']}" if p1 else "Unknown",
            "p2_name": f"{p2['first_name']} {p2['last_name']}" if p2 else "Unknown"
        })
    return templates.TemplateResponse(request=request, name="matches.html", context={"matches": enriched})

@app.get("/sessions/")
async def list_sessions(request: Request, filter: str = "all"):
    db = await get_db()
    from datetime import datetime
    now = datetime.utcnow()
    
    query = {}
    if filter == "upcoming":
        query = {"start_date": {"$gt": now}}
    elif filter == "ongoing":
        query = {"start_date": {"$lte": now}, "end_date": {"$gte": now}}
    elif filter == "past":
        query = {"end_date": {"$lt": now}}
    # "all" is implicit (empty query)
        
    cursor = db.sessions.find(query).sort("start_date", 1 if filter == "upcoming" else -1)
    sessions = [Session(**{**s, "id": str(s["_id"])}) async for s in cursor]
    
    return templates.TemplateResponse(request=request, name="sessions.html", context={
        "sessions": sessions, 
        "now_date": now.strftime("%Y-%m-%d"),
        "filter": filter
    })

@app.post("/sessions/create")
async def create_session(request: Request):
    data = await request.form()
    from datetime import datetime, timedelta
    
    date_str = data.get("date")
    start_time = data.get("start_time")
    duration = int(data.get("duration_minutes", 60))
    
    start_date = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
    end_date = start_date + timedelta(minutes=duration)
    
    num_courts = int(data.get("num_courts", 0))
    location = data.get("location", "Finsbury Leisure Centre")
    max_players_input = data.get("max_players")
    
    # Logic: if max_players is null, derive from num_courts (3 players per court)
    if max_players_input:
        max_players = int(max_players_input)
    elif num_courts > 0:
        max_players = num_courts * 3
    else:
        max_players = None
    
    session = Session(
        start_date=start_date, 
        end_date=end_date, 
        num_courts=num_courts,
        location=location,
        max_players=max_players
    )
    db = await get_db()
    await db.sessions.insert_one(session.model_dump(exclude={"id"}))
    
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/sessions/", status_code=303)

@app.post("/sessions/{session_id}/join")
async def join_session(session_id: str, request: Request):
    # Hardcoded test user ID
    TEST_USER_ID = "66358f000000000000000000"
    
    db = await get_db()
    session_doc = await db.sessions.find_one({"_id": ObjectId(session_id)})
    
    if not session_doc:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = Session(**{**session_doc, "id": str(session_doc["_id"])})
    
    # Check capacity
    if session.max_players and len(session.player_ids) >= session.max_players:
        raise HTTPException(status_code=400, detail="Session is full")
        
    if TEST_USER_ID not in session.player_ids:
        await db.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$push": {"player_ids": TEST_USER_ID}}
        )
        
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/sessions/", status_code=303)

@app.get("/sessions/{session_id}")
async def read_session(session_id: str, request: Request):
    db = await get_db()
    try:
        session_doc = await db.sessions.find_one({"_id": ObjectId(session_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid session ID")
    
    if not session_doc:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = Session(**{**session_doc, "id": str(session_doc["_id"])})
    
    # Get player details
    players = []
    for pid in session.player_ids:
        try:
            p = await db.profiles.find_one({"_id": ObjectId(pid)})
            if p:
                players.append(f"{p['first_name']} {p['last_name']}")
        except:
            continue
            
    # Get matches for this session
    matches_cursor = db.matches.find({"session_id": session_id})
    matches = []
    async for m in matches_cursor:
        m_obj = Match(**{**m, "id": str(m["_id"])})
        p1 = await db.profiles.find_one({"_id": ObjectId(m_obj.player1_id)})
        p2 = await db.profiles.find_one({"_id": ObjectId(m_obj.player2_id)})
        matches.append({
            "match": m_obj,
            "p1_name": f"{p1['first_name']} {p1['last_name']}" if p1 else "Unknown",
            "p2_name": f"{p2['first_name']} {p2['last_name']}" if p2 else "Unknown"
        })
            
    return templates.TemplateResponse(request=request, name="session_detail.html", context={
        "session": session,
        "players": players,
        "matches": matches
    })
