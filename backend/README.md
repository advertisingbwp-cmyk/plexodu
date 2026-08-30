# Plexudo Backend

This is Phase 1 of the Plexudo Backend.

## Tech Stack
- FastAPI
- PostgreSQL + AsyncPG
- SQLAlchemy 2.0 (Async)
- Alembic
- Pytest

## Setup

1. Copy `.env.example` to `.env` and fill in the values.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(We are using pyproject.toml, so `pip install -e .[dev]`)*
3. Run DB Migrations:
   ```bash
   alembic upgrade head
   ```
4. Run server:
   ```bash
   uvicorn app.main:app --reload
   ```
5. Run tests:
   ```bash
   pytest
   ```
