"""
FastAPI backend for focus group sessions.

Run with: uvicorn src.api:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from personas.selection import select_personas
from src.claude import get_client, run_focus_group
from src.db import get_conn
from src.sessions import (
    create_session,
    save_responses,
    complete_session,
    fail_session,
    get_session,
    list_sessions,
)

app = FastAPI(title="Focus Groups API", version="0.1.0")


# ── Request / Response models ─────────────────────────────────────────────────

class SessionRequest(BaseModel):
    question: str
    num_personas: int
    sector: str | None = None
    demographic_filter: dict | None = None


class SessionCreated(BaseModel):
    session_id: int
    status: str
    num_responses: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/sessions", response_model=SessionCreated)
def create_session_endpoint(req: SessionRequest):
    """
    Create a focus group session: select personas, run Claude, store results.
    """
    conn = get_conn()
    demo_filter = req.demographic_filter or {}

    # Select diverse personas
    cards = select_personas(
        conn,
        demographic_filter=demo_filter,
        sector=req.sector,
        n=req.num_personas,
    )

    if not cards:
        raise HTTPException(status_code=404, detail="No personas found matching the given filters.")

    # Create session record
    session_id = create_session(
        conn,
        sector=req.sector,
        demographic_filter=demo_filter,
        num_personas=req.num_personas,
        question=req.question,
    )

    # Run focus group through Claude
    try:
        client = get_client()
        responses = run_focus_group(client, cards, req.question)
        save_responses(conn, session_id, responses)
        complete_session(conn, session_id)
    except Exception:
        fail_session(conn, session_id)
        raise HTTPException(status_code=500, detail="Focus group generation failed.")
    finally:
        conn.close()

    return SessionCreated(
        session_id=session_id,
        status="completed",
        num_responses=len(responses),
    )


@app.get("/sessions/{session_id}")
def get_session_endpoint(session_id: int):
    """Get a session with all its responses."""
    conn = get_conn()
    try:
        session = get_session(conn, session_id)
    finally:
        conn.close()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    return session


@app.get("/sessions")
def list_sessions_endpoint(limit: int = Query(default=20, ge=1, le=100)):
    """List recent sessions."""
    conn = get_conn()
    try:
        sessions = list_sessions(conn, limit=limit)
    finally:
        conn.close()

    return sessions
