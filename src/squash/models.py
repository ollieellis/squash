from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class Profile(BaseModel):
    id: Optional[str] = None
    first_name: str
    last_name: str
    email: Optional[str] = None
    password_hash: Optional[str] = None
    elo: float = 1200.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Session(BaseModel):
    id: Optional[str] = None
    start_date: datetime
    end_date: datetime
    location: str = "Finsbury Leisure Centre"
    player_ids: list[str] = []
    num_courts: int = 0
    max_players: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Match(BaseModel):
    id: Optional[str] = None
    player1_id: str
    player2_id: str
    player1_score: int
    player2_score: int
    winner_id: str
    elo_change: float
    session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class EloHistory(BaseModel):
    id: Optional[str] = None
    profile_id: str
    elo_value: float
    match_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
