from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class Profile(BaseModel):
    id: Optional[str] = None
    first_name: str
    last_name: str
    elo: int = 1200
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Match(BaseModel):
    id: Optional[str] = None
    player1_id: str
    player2_id: str
    player1_score: int
    player2_score: int
    winner_id: str
    elo_change: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
