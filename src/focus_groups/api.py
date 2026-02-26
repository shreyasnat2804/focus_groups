"""
FastAPI backend for focus group sessions.

Run with: uvicorn focus_groups.api:app --reload
"""

from __future__ import annotations

from io import BytesIO
from typing import Literal, Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, model_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from focus_groups.auth import require_api_key

from focus_groups.export import export_csv, export_pdf
from focus_groups.personas.cards import PersonaCard
from focus_groups.personas.selection import select_personas
from focus_groups.claude import get_client, run_focus_group
from focus_groups.db import get_conn, get_posts_by_ids
from focus_groups.wtp.van_westendorp import (
    collect_psm_responses,
    compute_psm_curves,
    find_price_points,
)
from focus_groups.wtp.gabor_granger import (
    collect_demand_responses,
    compute_demand_curve,
)
from focus_groups.wtp.segmentation import segment_psm_by, segment_demand_by
from focus_groups.wtp.pricing_models import build_hybrid_price_points, normalize_for_display
from focus_groups.sessions import (
    count_sessions,
    create_session,
    save_responses,
    complete_session,
    fail_session,
    get_session,
    list_sessions,
    update_session_question,
    update_session_name,
    delete_responses,
    soft_delete_session,
    restore_session,
    purge_expired_sessions,
    permanently_delete_session,
)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Focus Groups API",
    version="0.1.0",
    dependencies=[Depends(require_api_key)],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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


class WtpRequest(BaseModel):
    pricing_model: Literal["one_time", "subscription", "hybrid"] = "one_time"
    price_points: list[int] = []
    upfront_price_points: Optional[list[float]] = None
    subscription_price_points: Optional[list[float]] = None
    billing_interval: Optional[Literal["monthly", "annual"]] = "monthly"
    segment_by: str = "income_bracket"

    @model_validator(mode="after")
    def hybrid_fields_required(self):
        if self.pricing_model == "hybrid":
            if self.upfront_price_points is None:
                raise ValueError("hybrid model requires upfront_price_points")
            if self.subscription_price_points is None:
                raise ValueError("hybrid model requires subscription_price_points")
        return self


def _derive_price_points(psm_pts: dict, n: int = 7) -> list[int]:
    """Generate Gabor-Granger price points from Van Westendorp results.

    Spans from ~20% below the acceptable range floor to ~20% above
    the ceiling, with n evenly spaced points rounded to nice numbers.
    """
    low, high = psm_pts["acceptable_range"]
    optimal = psm_pts["optimal_price"]

    # Extend range 20% beyond the acceptable bounds
    margin = max((high - low) * 0.2, optimal * 0.1, 1)
    floor = max(1, low - margin)
    ceil = high + margin

    step = (ceil - floor) / (n - 1)

    # Round to a "nice" step: nearest 1, 5, 10, 25, 50, 100 etc.
    nice_steps = [1, 2, 5, 10, 15, 20, 25, 50, 75, 100, 150, 200, 250, 500]
    nice_step = min(nice_steps, key=lambda s: abs(s - step)) or 1

    # Build points from floor, rounded to nice_step
    base = max(1, round(floor / nice_step) * nice_step)
    points = []
    p = base
    while p <= ceil + nice_step and len(points) < n + 2:
        points.append(int(p))
        p += nice_step

    # Deduplicate and ensure at least 2 points
    points = sorted(set(points))
    if len(points) < 2:
        points = [max(1, int(optimal * 0.5)), int(optimal), int(optimal * 1.5)]

    return points


class RenameRequest(BaseModel):
    name: str | None


class SessionCreated(BaseModel):
    session_id: str
    status: str
    num_responses: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/api/sessions", response_model=SessionCreated)
@limiter.limit("5/minute")
def create_session_endpoint(request: Request, req: SessionRequest):
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
@limiter.limit("30/minute")
def get_session_endpoint(request: Request, session_id: str):
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
@limiter.limit("30/minute")
def list_sessions_endpoint(
    request: Request,
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
@limiter.limit("20/minute")
def delete_session_endpoint(request: Request, session_id: str):
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
@limiter.limit("20/minute")
def restore_session_endpoint(request: Request, session_id: str):
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
@limiter.limit("20/minute")
def permanently_delete_session_endpoint(request: Request, session_id: str):
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


@app.patch("/api/sessions/{session_id}/name")
@limiter.limit("20/minute")
def rename_session_endpoint(request: Request, session_id: str, req: RenameRequest):
    """Update the display name for a session."""
    conn = get_conn()
    try:
        session = get_session(conn, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        update_session_name(conn, session_id, req.name)
    finally:
        conn.close()
    return {"session_id": session_id, "name": req.name}


@app.post("/api/sessions/{session_id}/rerun", response_model=SessionCreated)
@limiter.limit("5/minute")
def rerun_session_endpoint(request: Request, session_id: str, req: RerunRequest):
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


@app.post("/api/sessions/{session_id}/wtp")
@limiter.limit("5/minute")
def run_wtp_endpoint(request: Request, session_id: str, req: WtpRequest):
    """
    Run Willingness to Pay analysis on an existing session's personas.

    Reconstructs PersonaCards from the session's response post_ids,
    runs Van Westendorp PSM and Gabor-Granger demand simulation,
    and returns full results with demographic segmentation.
    """
    conn = get_conn()
    try:
        session = get_session(conn, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")

        responses = session.get("responses", [])
        if not responses:
            raise HTTPException(status_code=400, detail="Session has no responses to analyze.")

        # Reconstruct PersonaCards from session responses
        post_ids = [r["post_id"] for r in responses if r.get("post_id")]
        posts = get_posts_by_ids(conn, post_ids)
    finally:
        conn.close()

    if not posts:
        raise HTTPException(status_code=400, detail="Could not load persona data for this session.")

    cards = [
        PersonaCard(
            post_id=p["post_id"],
            demographic_tags=p["demographic_tags"],
            text_excerpt=p["text"][:300],
            sector=p["sector"],
        )
        for p in posts
    ]

    # Extract product description from the session question
    product = session["question"]

    try:
        client = get_client()
        pricing_model = req.pricing_model

        # Van Westendorp PSM
        psm_raw = collect_psm_responses(client, cards, product, pricing_model=pricing_model)
        psm_curves = compute_psm_curves(psm_raw)
        psm_pts = find_price_points(psm_curves)

        # Build hybrid tiers if applicable
        hybrid_tiers = None
        if pricing_model == "hybrid":
            hybrid_tiers = build_hybrid_price_points(
                req.upfront_price_points, req.subscription_price_points
            )

        # Derive Gabor-Granger price points from PSM if not provided
        price_points = req.price_points
        if not price_points:
            if pricing_model == "hybrid" and hybrid_tiers:
                price_points = [t["total_12m"] for t in hybrid_tiers]
            else:
                price_points = _derive_price_points(psm_pts)

        # Gabor-Granger
        demand_raw = collect_demand_responses(
            client, cards, product, price_points,
            pricing_model=pricing_model, hybrid_tiers=hybrid_tiers,
        )
        demand_curve = compute_demand_curve(demand_raw, price_points)

        # Segmented analysis
        psm_segments = segment_psm_by(psm_raw, req.segment_by)
        demand_segments = segment_demand_by(demand_raw, req.segment_by)

        # Compute curves per segment
        segment_psm_results = {}
        for seg_name, seg_data in psm_segments.items():
            if len(seg_data) >= 2:
                seg_curves = compute_psm_curves(seg_data)
                seg_pts = find_price_points(seg_curves)
                segment_psm_results[seg_name] = {
                    "optimal_price": seg_pts["optimal_price"],
                    "acceptable_range": seg_pts["acceptable_range"],
                    "n": len(seg_data),
                }

        segment_demand_results = {}
        for seg_name, seg_data in demand_segments.items():
            seg_curve = compute_demand_curve(seg_data, price_points)
            segment_demand_results[seg_name] = seg_curve

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"WTP analysis failed: {e}")

    # Build response
    result = {
        "session_id": session_id,
        "num_personas": len(cards),
        "pricing_model": pricing_model,
        "van_westendorp": {
            "responses": psm_raw,
            "curves": psm_curves,
            "optimal_price": psm_pts["optimal_price"],
            "acceptable_range": psm_pts["acceptable_range"],
        },
        "gabor_granger": {
            "responses": demand_raw,
            "demand_curve": demand_curve,
        },
        "segments": {
            "dimension": req.segment_by,
            "psm": segment_psm_results,
            "demand": segment_demand_results,
        },
    }

    # Add hybrid-specific fields
    if pricing_model == "hybrid" and hybrid_tiers:
        result["hybrid_tiers"] = hybrid_tiers
        result["normalized_price_points"] = sorted(t["total_12m"] for t in hybrid_tiers)

    return result


@app.get("/api/sessions/{session_id}/export/csv")
@limiter.limit("10/minute")
def export_csv_endpoint(request: Request, session_id: str):
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
@limiter.limit("10/minute")
def export_pdf_endpoint(request: Request, session_id: str):
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
