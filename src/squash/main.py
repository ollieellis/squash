from fastapi import FastAPI, Depends, HTTPException, Request, Response, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from .database import connect_to_mongo, close_mongo_connection, get_db
from .models import Profile, Match, Session, EloHistory
from .elo import calculate_squash_elo
from .auth import verify_password, get_password_hash, create_access_token, decode_access_token
from contextlib import asynccontextmanager
from bson import ObjectId
from typing import Optional

@asynccontextmanager
async def lifespan(app: FastAPI):
    connect_to_mongo()
    yield
    close_mongo_connection()

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# Auth Dependency
async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    db = await get_db()
    user_doc = await db.profiles.find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        return None
    return Profile(**{**user_doc, "id": str(user_doc["_id"])})

async def login_required(user: Optional[Profile] = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user

@app.get("/")
async def root(request: Request):
    return RedirectResponse(url="/profiles/", status_code=303)

@app.get("/login")
async def login_page(request: Request, next: Optional[str] = None):
    return templates.TemplateResponse(request=request, name="login.html", context={"next_url": next})

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), next: Optional[str] = Form(None)):
    db = await get_db()
    user_doc = await db.profiles.find_one({"email": email})
    if not user_doc or not user_doc.get("password_hash") or not verify_password(password, user_doc["password_hash"]):
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid email or password", "next_url": next})
    
    access_token = create_access_token(data={"sub": str(user_doc["_id"])})
    redirect_url = next if next else "/"
    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/register")
async def register_page(request: Request, next: Optional[str] = None):
    return templates.TemplateResponse(request=request, name="register.html", context={"next_url": next})

@app.post("/register")
async def register(request: Request, first_name: str = Form(...), last_name: str = Form(...), email: str = Form(...), password: str = Form(...), next: Optional[str] = Form(None)):
    db = await get_db()
    existing = await db.profiles.find_one({"email": email})
    if existing:
        return templates.TemplateResponse(request=request, name="register.html", context={"error": "Email already registered", "next_url": next})
    
    hashed_password = get_password_hash(password)
    profile = Profile(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=hashed_password
    )
    
    result = await db.profiles.insert_one(profile.model_dump(exclude={"id"}))
    user_id = str(result.inserted_id)
    
    # Record initial ELO history
    await db.elo_history.insert_one(
        EloHistory(profile_id=user_id, elo_value=profile.elo).model_dump(exclude={"id"})
    )
    
    access_token = create_access_token(data={"sub": user_id})
    redirect_url = next if next else "/"
    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response

@app.get("/profiles/")
async def list_profiles(request: Request, user: Optional[Profile] = Depends(get_current_user)):
    db = await get_db()
    profiles_cursor = db.profiles.find().sort("elo", -1)
    profiles = [Profile(**{**doc, "id": str(doc["_id"])}) async for doc in profiles_cursor]
    
    # Enrich with recent form
    enriched_profiles = []
    for p in profiles:
        matches_cursor = db.matches.find({"$or": [{"player1_id": p.id}, {"player2_id": p.id}]}).sort("created_at", -1).limit(5)
        recent_matches = []
        async for m in matches_cursor:
            match = Match(**{**m, "id": str(m["_id"])})
            res = "D" if match.winner_id == "draw" else ("W" if match.winner_id == p.id else "L")
            recent_matches.append(res)
        enriched_profiles.append({"profile": p, "form": recent_matches})
        
    return templates.TemplateResponse(request=request, name="profiles.html", context={"profiles": enriched_profiles, "user": user})

@app.get("/profiles/{profile_id}")
async def read_profile(profile_id: str, request: Request, range: str = "6m", user: Optional[Profile] = Depends(get_current_user)):
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

    # Fetch ELO History for Graphing
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    history_query = {"profile_id": profile_id}
    
    if range == "1m":
        history_query["timestamp"] = {"$gte": now - timedelta(days=30)}
    elif range == "3m":
        history_query["timestamp"] = {"$gte": now - timedelta(days=90)}
    elif range == "6m":
        history_query["timestamp"] = {"$gte": now - timedelta(days=180)}
    # "all" or invalid range shows everything

    history_cursor = db.elo_history.find(history_query).sort("timestamp", 1)
    history_data = []
    async for h in history_cursor:
        history_data.append({
            "t": h["timestamp"].isoformat(),
            "v": h["elo_value"]
        })

    return templates.TemplateResponse(request=request, name="profile.html", context={
        "profile": profile, 
        "form_guide": form_guide, 
        "recent_matches": recent_matches, 
        "user": user,
        "history_data": history_data,
        "current_range": range
    })

@app.post("/matches/")
async def log_match(request: Request, user: Profile = Depends(login_required)):
    data = await request.form()
    p1_id = data.get("player1_id")
    p2_id = data.get("player2_id")
    
    # Ensure the logged in user is one of the players (optional, but good practice)
    # if user.id not in [p1_id, p2_id]:
    #     raise HTTPException(status_code=403, detail="You can only log matches you played in")

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
    
    session_id = data.get("session_id") or None
    
    match = Match(
        player1_id=p1_id, 
        player2_id=p2_id, 
        player1_score=p1_score, 
        player2_score=p2_score, 
        winner_id=winner_id, 
        elo_change=delta,
        session_id=session_id
    )
    match_result = await db.matches.insert_one(match.model_dump(exclude={"id"}))
    match_id = str(match_result.inserted_id)
    
    # Record ELO History
    await db.elo_history.insert_many([
        EloHistory(profile_id=p1_id, elo_value=new_p1_elo, match_id=match_id, session_id=session_id).model_dump(exclude={"id"}),
        EloHistory(profile_id=p2_id, elo_value=new_p2_elo, match_id=match_id, session_id=session_id).model_dump(exclude={"id"})
    ])
    
    return templates.TemplateResponse(request=request, name="match_success.html", context={
        "match_id": match_id, "p1_name": f"{p1['first_name']} {p1['last_name']}",
        "p2_name": f"{p2['first_name']} {p2['last_name']}", "delta": delta,
        "user": user
    })

@app.get("/matches/{match_id}")
async def read_match(match_id: str, request: Request, user: Optional[Profile] = Depends(get_current_user)):
    db = await get_db()
    try:
        match_doc = await db.matches.find_one({"_id": ObjectId(match_id)})
    except:
        raise HTTPException(status_code=404, detail="Invalid match ID")
    
    if not match_doc:
        raise HTTPException(status_code=404, detail="Match not found")
        
    p1 = await db.profiles.find_one({"_id": ObjectId(match_doc["player1_id"])})
    p2 = await db.profiles.find_one({"_id": ObjectId(match_doc["player2_id"])})
    
    # Get all sessions for assignment
    sessions_cursor = db.sessions.find().sort("start_date", -1)
    sessions = [Session(**{**s, "id": str(s["_id"])}) async for s in sessions_cursor]
    
    current_session = None
    if match_doc.get("session_id"):
        current_session = await db.sessions.find_one({"_id": ObjectId(match_doc["session_id"])})

    return templates.TemplateResponse(request=request, name="match.html", context={
        "match": match_doc, 
        "p1_name": f"{p1['first_name']} {p1['last_name']}" if p1 else "Unknown",
        "p2_name": f"{p2['first_name']} {p2['last_name']}" if p2 else "Unknown",
        "user": user,
        "sessions": sessions,
        "current_session": current_session
    })

@app.post("/matches/{match_id}/session")
async def update_match_session(match_id: str, session_id: str = Form(...), user: Profile = Depends(login_required)):
    db = await get_db()
    await db.matches.update_one(
        {"_id": ObjectId(match_id)},
        {"$set": {"session_id": session_id if session_id != "none" else None}}
    )
    return RedirectResponse(url=f"/matches/{match_id}", status_code=303)

async def get_modal_data(db):
    profiles_cursor = db.profiles.find().sort("first_name", 1)
    profiles = [Profile(**{**doc, "id": str(doc["_id"])}) async for doc in profiles_cursor]
    
    from datetime import datetime, timedelta
    recent_sessions_cursor = db.sessions.find({
        "start_date": {"$gte": datetime.utcnow() - timedelta(days=7)}
    }).sort("start_date", -1)
    recent_sessions = [Session(**{**s, "id": str(s["_id"])}) async for s in recent_sessions_cursor]
    
    return profiles, recent_sessions

@app.get("/matches/")
async def list_matches(request: Request, user: Optional[Profile] = Depends(get_current_user)):
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
    
    profiles, recent_sessions = await get_modal_data(db)
    
    return templates.TemplateResponse(request=request, name="matches.html", context={
        "matches": enriched, 
        "user": user,
        "profiles_for_modal": profiles,
        "sessions_for_modal": recent_sessions
    })

@app.get("/sessions/")
async def list_sessions(request: Request, filter: str = "all", user: Optional[Profile] = Depends(get_current_user)):
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
        "filter": filter,
        "user": user
    })

@app.post("/sessions/create")
async def create_session(request: Request, user: Profile = Depends(login_required)):
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
    
    return RedirectResponse(url="/sessions/", status_code=303)

@app.post("/sessions/{session_id}/join")
async def join_session(session_id: str, request: Request, user: Profile = Depends(login_required)):
    db = await get_db()
    session_doc = await db.sessions.find_one({"_id": ObjectId(session_id)})
    
    if not session_doc:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = Session(**{**session_doc, "id": str(session_doc["_id"])})
    
    # Check capacity
    if session.max_players and len(session.player_ids) >= session.max_players:
        raise HTTPException(status_code=400, detail="Session is full")
        
    if user.id not in session.player_ids:
        await db.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$push": {"player_ids": user.id}}
        )
        
    return RedirectResponse(url="/sessions/", status_code=303)

@app.get("/sessions/{session_id}")
async def read_session(session_id: str, request: Request, user: Optional[Profile] = Depends(get_current_user)):
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
            
    # Get profiles and recent sessions for the Log Match modal
    profiles, recent_sessions = await get_modal_data(db)
            
    return templates.TemplateResponse(request=request, name="session_detail.html", context={
        "session": session,
        "players": players,
        "matches": matches,
        "user": user,
        "profiles_for_modal": profiles,
        "sessions_for_modal": recent_sessions,
        "preselected_session_id": session_id
    })


@app.post("/inbox/report")
async def report_bug(title: str = Form(...), text: str = Form(...), user: Optional[Profile] = Depends(get_current_user)):
    db = await get_db()
    from datetime import datetime
    entry = {"title": title, "text": text, "created_at": datetime.utcnow(), "user_id": user.id if user else None}
    await db.inbox_entries.insert_one(entry)
    return {"ok": True}
