"""
FastAPI backend for focus group sessions.

Run with: uvicorn focus_groups.api:app --reload
"""

from __future__ import annotations

from io import BytesIO

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from focus_groups.export import export_csv, export_pdf
from focus_groups.personas.selection import select_personas
from focus_groups.claude import get_client, run_focus_group
from focus_groups.db import get_conn
from focus_groups.sessions import (
    count_sessions,
    create_session,
    save_responses,
    complete_session,
    fail_session,
    get_session,
    list_sessions,
    update_session_question,
    delete_responses,
    soft_delete_session,
    restore_session,
    purge_expired_sessions,
    permanently_delete_session,
)

app = FastAPI(title="Focus Groups API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class SessionRequest(BaseModel):
    question: str
    num_personas: int
    sector: str | None = None
    demographic_filter: dict | None = None


class RerunRequest(BaseModel):
    question: str
    sector: str | None = None
    num_personas: int | None = None
    demographic_filter: dict | None = None


class SessionCreated(BaseModel):
    session_id: str
    status: str
    num_responses: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/api/sessions", response_model=SessionCreated)
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
    except Exception as e:
        import traceback
        traceback.print_exc()
        fail_session(conn, session_id)
        raise HTTPException(status_code=500, detail=f"Focus group generation failed: {e}")
    finally:
        conn.close()

    return SessionCreated(
        session_id=session_id,
        status="completed",
        num_responses=len(responses),
    )


@app.get("/api/sessions/{session_id}")
def get_session_endpoint(session_id: str):
    """Get a session with all its responses."""
    conn = get_conn()
    try:
        session = get_session(conn, session_id)
    finally:
        conn.close()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    return session


@app.get("/api/sessions")
def list_sessions_endpoint(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    sector: str | None = Query(default=None),
    deleted: bool = Query(default=False),
):
    """List recent sessions with pagination, search, and filters."""
    conn = get_conn()
    try:
        # Purge sessions deleted more than 30 days ago
        purge_expired_sessions(conn)

        total = count_sessions(conn, search=search, sector=sector, deleted=deleted)
        if offset >= total and total > 0:
            offset = max(0, (total - 1) // limit * limit)
        sessions = list_sessions(
            conn, limit=limit, offset=offset,
            search=search, sector=sector, deleted=deleted,
        )
    finally:
        conn.close()

    return {
        "items": sessions,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }


@app.delete("/api/sessions/{session_id}")
def delete_session_endpoint(session_id: str):
    """Soft delete a session (move to trash)."""
    conn = get_conn()
    try:
        session = get_session(conn, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        soft_delete_session(conn, session_id)
    finally:
        conn.close()
    return {"status": "deleted", "session_id": session_id}


@app.post("/api/sessions/{session_id}/restore")
def restore_session_endpoint(session_id: str):
    """Restore a soft-deleted session from trash."""
    conn = get_conn()
    try:
        session = get_session(conn, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        restore_session(conn, session_id)
    finally:
        conn.close()
    return {"status": "restored", "session_id": session_id}


@app.delete("/api/sessions/{session_id}/permanent")
def permanently_delete_session_endpoint(session_id: str):
    """Permanently delete a session (cannot be undone)."""
    conn = get_conn()
    try:
        session = get_session(conn, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        permanently_delete_session(conn, session_id)
    finally:
        conn.close()
    return {"status": "permanently_deleted", "session_id": session_id}


@app.post("/api/sessions/{session_id}/rerun", response_model=SessionCreated)
def rerun_session_endpoint(session_id: str, req: RerunRequest):
    """
    Re-run a session: update question, delete old responses, re-select
    personas, run Claude, save new responses.

    Optional overrides for sector, num_personas, and demographic_filter
    fall back to the session's existing values if not provided.
    """
    conn = get_conn()
    try:
        session = get_session(conn, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")

        # Use overrides or fall back to existing session values
        sector = req.sector if req.sector is not None else session["sector"]
        num_personas = req.num_personas if req.num_personas is not None else session["num_personas"]
        demo_filter = req.demographic_filter if req.demographic_filter is not None else (session["demographic_filter"] or {})

        # Update question and clear old responses
        update_session_question(conn, session_id, req.question)
        delete_responses(conn, session_id)

        # Re-select personas and run
        cards = select_personas(
            conn,
            demographic_filter=demo_filter,
            sector=sector,
            n=num_personas,
        )

        if not cards:
            raise HTTPException(status_code=404, detail="No personas found matching the given filters.")

        client = get_client()
        responses = run_focus_group(client, cards, req.question)
        save_responses(conn, session_id, responses)
        complete_session(conn, session_id)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        fail_session(conn, session_id)
        raise HTTPException(status_code=500, detail=f"Focus group re-run failed: {e}")
    finally:
        conn.close()

    return SessionCreated(
        session_id=session_id,
        status="completed",
        num_responses=len(responses),
    )


@app.get("/api/sessions/{session_id}/export/csv")
def export_csv_endpoint(session_id: str):
    """Export a session as CSV."""
    conn = get_conn()
    try:
        session = get_session(conn, session_id)
    finally:
        conn.close()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    csv_text = export_csv(session)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=session_{session_id}.csv"},
    )


@app.get("/api/sessions/{session_id}/export/pdf")
def export_pdf_endpoint(session_id: str):
    """Export a session as PDF."""
    conn = get_conn()
    try:
        session = get_session(conn, session_id)
    finally:
        conn.close()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    pdf_bytes = export_pdf(session)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=session_{session_id}.pdf"},
    )
