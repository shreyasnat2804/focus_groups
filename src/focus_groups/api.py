"""
FastAPI backend for focus group sessions.

Run with: uvicorn focus_groups.api:app --reload
"""

from __future__ import annotations

import logging
import os
import re
import time
from contextlib import asynccontextmanager
from io import BytesIO
from typing import Literal, Optional

from dotenv import load_dotenv
load_dotenv()

ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000",
).split(",")

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, model_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from focus_groups.auth import require_api_key

from focus_groups.export import export_csv, export_pdf
from focus_groups.personas.cards import PersonaCard
from focus_groups.personas.selection import select_personas
from focus_groups.claude import get_client, run_focus_group
from focus_groups.db import get_conn, get_pool_conn, return_pool_conn, init_pool, close_pool, get_posts_by_ids
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

logger = logging.getLogger(__name__)


def _safe_filename(name: str) -> str:
    """Remove any characters that could cause header injection."""
    return re.sub(r'[^a-zA-Z0-9_-]', '', name)

_last_purge: float = 0
PURGE_INTERVAL = 3600  # seconds — purge expired sessions at most once per hour

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    yield
    close_pool()


app = FastAPI(
    title="Focus Groups API",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Health check endpoints (no auth, no rate limiting) ────────────────────────

@app.get("/health")
def liveness():
    """Liveness probe: is the process running?"""
    return {"status": "ok"}


@app.get("/ready")
def readiness():
    """Readiness probe: can we serve traffic?

    Grabs a connection from the pool, runs SELECT 1, returns it.
    Returns 503 if the pool is exhausted or DB is unreachable.
    """
    try:
        conn = get_pool_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        finally:
            return_pool_conn(conn)
    except Exception:
        logger.warning("Readiness check failed", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "detail": "Database connection failed"},
        )
    return {"status": "ready"}


def get_db():
    """FastAPI dependency: yield a pooled connection, always returned."""
    conn = get_pool_conn()
    try:
        yield conn
    finally:
        return_pool_conn(conn)


# ── Request / Response models ─────────────────────────────────────────────────

class SessionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    num_personas: int = Field(ge=1, le=50)
    sector: Literal["tech", "financial", "political"] | None = None
    demographic_filter: dict | None = None


class RerunRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    sector: Literal["tech", "financial", "political"] | None = None
    num_personas: int | None = Field(default=None, ge=1, le=50)
    demographic_filter: dict | None = None


class WtpRequest(BaseModel):
    pricing_model: Literal["one_time", "subscription", "hybrid"] = "one_time"
    price_points: list[int] = []
    upfront_price_points: Optional[list[float]] = None
    subscription_price_points: Optional[list[float]] = None
    billing_interval: Optional[Literal["monthly", "annual"]] = "monthly"
    segment_by: Literal[
        "age_group", "gender", "income_bracket",
        "education_level", "region"
    ] = "income_bracket"

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


# ── Business endpoints (auth required) ────────────────────────────────────────

api_router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


@api_router.post("/sessions", response_model=SessionCreated)
@limiter.limit("5/minute")
def create_session_endpoint(request: Request, req: SessionRequest, conn=Depends(get_db)):
    """
    Create a focus group session: select personas, run Claude, store results.
    """
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
        logger.exception("Focus group generation failed")
        fail_session(conn, session_id)
        raise HTTPException(status_code=500, detail="Focus group generation failed. Please try again.")

    return SessionCreated(
        session_id=session_id,
        status="completed",
        num_responses=len(responses),
    )


@api_router.get("/sessions/{session_id}")
@limiter.limit("30/minute")
def get_session_endpoint(request: Request, session_id: str, conn=Depends(get_db)):
    """Get a session with all its responses."""
    session = get_session(conn, session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    return session


@api_router.get("/sessions")
@limiter.limit("30/minute")
def list_sessions_endpoint(
    request: Request,
    conn=Depends(get_db),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    sector: str | None = Query(default=None),
    deleted: bool = Query(default=False),
):
    """List recent sessions with pagination, search, and filters."""
    # Purge sessions deleted more than 30 days ago (throttled to once per hour)
    global _last_purge
    if time.time() - _last_purge > PURGE_INTERVAL:
        purge_expired_sessions(conn)
        _last_purge = time.time()

    total = count_sessions(conn, search=search, sector=sector, deleted=deleted)
    if offset >= total and total > 0:
        offset = max(0, (total - 1) // limit * limit)
    sessions = list_sessions(
        conn, limit=limit, offset=offset,
        search=search, sector=sector, deleted=deleted,
    )

    return {
        "items": sessions,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }


@api_router.delete("/sessions/{session_id}")
@limiter.limit("20/minute")
def delete_session_endpoint(request: Request, session_id: str, conn=Depends(get_db)):
    """Soft delete a session (move to trash)."""
    session = get_session(conn, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    soft_delete_session(conn, session_id)
    return {"status": "deleted", "session_id": session_id}


@api_router.post("/sessions/{session_id}/restore")
@limiter.limit("20/minute")
def restore_session_endpoint(request: Request, session_id: str, conn=Depends(get_db)):
    """Restore a soft-deleted session from trash."""
    session = get_session(conn, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    restore_session(conn, session_id)
    return {"status": "restored", "session_id": session_id}


@api_router.delete("/sessions/{session_id}/permanent")
@limiter.limit("20/minute")
def permanently_delete_session_endpoint(request: Request, session_id: str, conn=Depends(get_db)):
    """Permanently delete a session (cannot be undone)."""
    session = get_session(conn, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    permanently_delete_session(conn, session_id)
    return {"status": "permanently_deleted", "session_id": session_id}


@api_router.patch("/sessions/{session_id}/name")
@limiter.limit("20/minute")
def rename_session_endpoint(request: Request, session_id: str, req: RenameRequest, conn=Depends(get_db)):
    """Update the display name for a session."""
    session = get_session(conn, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    update_session_name(conn, session_id, req.name)
    return {"session_id": session_id, "name": req.name}


@api_router.post("/sessions/{session_id}/rerun", response_model=SessionCreated)
@limiter.limit("5/minute")
def rerun_session_endpoint(request: Request, session_id: str, req: RerunRequest, conn=Depends(get_db)):
    """
    Re-run a session: update question, delete old responses, re-select
    personas, run Claude, save new responses.

    Optional overrides for sector, num_personas, and demographic_filter
    fall back to the session's existing values if not provided.
    """
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

    try:
        client = get_client()
        responses = run_focus_group(client, cards, req.question)
        save_responses(conn, session_id, responses)
        complete_session(conn, session_id)
    except Exception:
        logger.exception("Focus group re-run failed")
        fail_session(conn, session_id)
        raise HTTPException(status_code=500, detail="Focus group re-run failed. Please try again.")

    return SessionCreated(
        session_id=session_id,
        status="completed",
        num_responses=len(responses),
    )


@api_router.post("/sessions/{session_id}/wtp")
@limiter.limit("5/minute")
def run_wtp_endpoint(request: Request, session_id: str, req: WtpRequest, conn=Depends(get_db)):
    """
    Run Willingness to Pay analysis on an existing session's personas.

    Reconstructs PersonaCards from the session's response post_ids,
    runs Van Westendorp PSM and Gabor-Granger demand simulation,
    and returns full results with demographic segmentation.
    """
    session = get_session(conn, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    responses = session.get("responses", [])
    if not responses:
        raise HTTPException(status_code=400, detail="Session has no responses to analyze.")

    # Reconstruct PersonaCards from session responses
    post_ids = [r["post_id"] for r in responses if r.get("post_id")]
    posts = get_posts_by_ids(conn, post_ids)

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

    except Exception:
        logger.exception("WTP analysis failed")
        raise HTTPException(status_code=500, detail="WTP analysis failed. Please try again.")

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


@api_router.get("/sessions/{session_id}/export/csv")
@limiter.limit("10/minute")
def export_csv_endpoint(request: Request, session_id: str, conn=Depends(get_db)):
    """Export a session as CSV."""
    session = get_session(conn, session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    csv_text = export_csv(session)
    safe_id = _safe_filename(session_id)
    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="session_{safe_id}.csv"'},
    )


@api_router.get("/sessions/{session_id}/export/pdf")
@limiter.limit("10/minute")
def export_pdf_endpoint(request: Request, session_id: str, conn=Depends(get_db)):
    """Export a session as PDF."""
    session = get_session(conn, session_id)

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    pdf_bytes = export_pdf(session)
    safe_id = _safe_filename(session_id)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="session_{safe_id}.pdf"'},
    )


app.include_router(api_router)
