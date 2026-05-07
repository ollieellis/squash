# Squash ELO & Session Organizer

A simple web application to organize squash sessions, track matches, and maintain an ELO-based ranking system. This tool is designed for internal use among colleagues to coordinate games, manage court bookings, and track competitive progress over time.

## Project Overview

- **Purpose:** Coordination and ranking system for squash enthusiasts.
- **Target Audience:** Colleagues and friends (internal use).
- **Core Features:**
    - **Session Coordination:** Create sessions, specify court counts, and allow players to join/leave.
    - **Match Logistics:** Log matches directly within a session context.
    - **Automatic ELO:** Real-time ranking updates using the `elosports` library.
    - **Player Profiles:** Detailed match history, form guides, and performance tracking.

## Tech Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.14+)
- **Database:** [MongoDB](https://www.mongodb.com/) (using Motor for async access).
- **Frontend:** Jinja2 templates (Server-side rendering).
- **Tooling:** [uv](https://github.com/astral-sh/uv) for dependency management and project execution.
- **Ranking Logic:** Custom ELO implementation with margin-of-victory considerations.

### Future Roadmap
- **Database Migration:** Currently using MongoDB locally, but there are plans to potentially migrate to **Firebase** for easier hosting and persistence. `firebase-admin` and `firebase-tools` are already included in the dependencies.

## Development Setup

### Prerequisites
- [uv](https://github.com/astral-sh/uv) installed.
- Docker (for local MongoDB).

### 1. Install Dependencies
Use `uv` to sync the environment:
```bash
uv sync
```

### 2. Start Database
Run MongoDB locally using Docker Compose:
```bash
docker-compose up -d
```
*Note: This also starts Mongo Express on http://localhost:8081 for easy database inspection.*

### 3. Initialize Data (Vibe Coding / Rapid Prototyping)
To quickly reset your environment or seed the database with sample players, sessions, and matches for "vibe coding":
```bash
# Seed sample data (Players, Sessions, and Matches)
uv run scripts/seed_dev.py

# Wipe the database clean
uv run scripts/drop_db.py
```

### 4. Run the Application
Start the FastAPI server:
```bash
uv run uvicorn main:app --reload
```
The application will be available at http://127.0.0.1:8000.

## Testing
Run the test suite using `pytest`:
```bash
uv run pytest
```

## Internal Note on Scaling
As this is a tool for colleagues, hyper-scalability is not a primary concern. The focus is on functionality, ease of maintenance, and rapid prototyping. Architectural choices like server-side rendering and simple MongoDB schemas reflect this priority.

---
*Maintained by the Squash Team*
