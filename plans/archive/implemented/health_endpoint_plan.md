# Fix: Add Health Check Endpoint — IMPLEMENTED 2026-02-27

## Problem
The API has no `/health` or `/ready` endpoint. Cloud Run (and any load balancer / orchestrator) requires a health check URL to determine instance readiness, route traffic, and restart unhealthy containers. Without one, Cloud Run falls back to TCP port checks which don't verify the app is actually functional — a half-started process with a bound port but a dead DB pool would still receive traffic.

## Severity: HIGH

## Approach: Liveness + Readiness Probes

Add two endpoints:
1. `/health` — lightweight liveness probe (is the process alive?)
2. `/ready` — readiness probe (can the app actually serve requests — is the DB pool healthy?)

The readiness probe runs `SELECT 1` against the connection pool. If the pool is exhausted or the DB is unreachable, it returns 503 so Cloud Run stops routing traffic to the instance.

Both endpoints are **excluded from authentication** (Cloud Run's health checker won't send an API key) and **excluded from rate limiting** (health checks fire every few seconds).

## Changes

### 1. Add health check endpoints to `src/focus_groups/api.py`

Add a separate router that bypasses the global `require_api_key` dependency:

```python
from fastapi import APIRouter

# Health check router — no auth, no rate limiting
health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def liveness():
    """Liveness probe: is the process running?"""
    return {"status": "ok"}


@health_router.get("/ready")
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
```

Register the router **before** the main app router so it isn't affected by global dependencies:

```python
# In the app setup section, after app = FastAPI(...):
app.include_router(health_router)
```

**Important**: because `health_router` is a separate `APIRouter` with no `dependencies` kwarg, it won't inherit the `dependencies=[Depends(require_api_key)]` from the `FastAPI(...)` constructor. Wait — actually, FastAPI's global `dependencies` **do** apply to all routes including included routers. To exempt the health routes from auth, we need a different approach.

**Correct approach**: Remove the global dependency from `FastAPI(...)` and instead apply `require_api_key` to a main `APIRouter` that holds all the business endpoints:

```python
# Option A: keep global deps, override on health endpoints
# This doesn't work cleanly with FastAPI.

# Option B (preferred): use a separate unauthenticated router
health_router = APIRouter(tags=["health"])
# ... health endpoints on health_router ...

api_router = APIRouter(
    prefix="/api",
    dependencies=[Depends(require_api_key)],
)
# ... move all /api/* endpoints to api_router ...

app = FastAPI(title="Focus Groups API", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)   # no auth
app.include_router(api_router)       # auth required
```

However, this is a significant refactor. **Simpler alternative**: keep the current structure but skip auth explicitly on health endpoints by not using the global dependency on the health router. Since all current endpoints are under `/api/` prefix, add the health routes at the root level and restructure the dependency:

```python
app = FastAPI(
    title="Focus Groups API",
    version="0.1.0",
    lifespan=lifespan,
    # REMOVE global dependency from here
)

# Auth-free health routes
@app.get("/health")
def liveness():
    return {"status": "ok"}

@app.get("/ready")
def readiness():
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

# All business endpoints get auth via api_router
api_router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])
# Move all existing @app.post("/api/sessions") etc. to @api_router.post("/sessions") etc.
app.include_router(api_router)
```

### 2. Refactor endpoint registration

Every existing endpoint changes from:
```python
@app.post("/api/sessions", response_model=SessionCreated)
@limiter.limit("5/minute")
def create_session_endpoint(request: Request, req: SessionRequest, conn=Depends(get_db)):
```

To:
```python
@api_router.post("/sessions", response_model=SessionCreated)
@limiter.limit("5/minute")
def create_session_endpoint(request: Request, req: SessionRequest, conn=Depends(get_db)):
```

Full mapping of changes:
| Old decorator | New decorator |
|---|---|
| `@app.post("/api/sessions", ...)` | `@api_router.post("/sessions", ...)` |
| `@app.get("/api/sessions/{session_id}")` | `@api_router.get("/sessions/{session_id}")` |
| `@app.get("/api/sessions")` | `@api_router.get("/sessions")` |
| `@app.delete("/api/sessions/{session_id}")` | `@api_router.delete("/sessions/{session_id}")` |
| `@app.post("/api/sessions/{session_id}/restore")` | `@api_router.post("/sessions/{session_id}/restore")` |
| `@app.delete("/api/sessions/{session_id}/permanent")` | `@api_router.delete("/sessions/{session_id}/permanent")` |
| `@app.patch("/api/sessions/{session_id}/name")` | `@api_router.patch("/sessions/{session_id}/name")` |
| `@app.post("/api/sessions/{session_id}/rerun", ...)` | `@api_router.post("/sessions/{session_id}/rerun", ...)` |
| `@app.post("/api/sessions/{session_id}/wtp")` | `@api_router.post("/sessions/{session_id}/wtp")` |
| `@app.get("/api/sessions/{session_id}/export/csv")` | `@api_router.get("/sessions/{session_id}/export/csv")` |
| `@app.get("/api/sessions/{session_id}/export/pdf")` | `@api_router.get("/sessions/{session_id}/export/pdf")` |

The `prefix="/api"` on the router means URLs don't change for callers.

### 3. Cloud Run configuration

When deploying, set the health check in `gcloud run deploy` or `service.yaml`:

```yaml
# Cloud Run service.yaml snippet
apiVersion: serving.knative.dev/v1
kind: Service
spec:
  template:
    spec:
      containers:
        - image: ...
          startupProbe:
            httpGet:
              path: /health
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /ready
            periodSeconds: 10
```

Or via CLI:
```bash
gcloud run deploy focus-groups-api \
  --startup-cpu-boost \
  --liveness-probe httpGet.path=/health \
  --startup-probe httpGet.path=/health
```

## Tests

### `tests/test_health.py`

```python
"""Tests for health check endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Test client with mocked DB pool."""
    with patch("focus_groups.api.init_pool"), \
         patch("focus_groups.api.close_pool"):
        from focus_groups.api import app
        yield TestClient(app)


class TestLiveness:
    """Tests for GET /health."""

    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_no_auth_required(self, client):
        """Health endpoint must work without X-API-Key header."""
        resp = client.get("/health")
        assert resp.status_code == 200


class TestReadiness:
    """Tests for GET /ready."""

    def test_returns_200_when_db_healthy(self, client):
        mock_conn = MagicMock()
        with patch("focus_groups.api.get_pool_conn", return_value=mock_conn), \
             patch("focus_groups.api.return_pool_conn"):
            resp = client.get("/ready")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ready"}

    def test_returns_503_when_db_unavailable(self, client):
        with patch("focus_groups.api.get_pool_conn", side_effect=Exception("pool exhausted")):
            resp = client.get("/ready")
        assert resp.status_code == 503
        assert resp.json()["status"] == "unavailable"

    def test_returns_503_when_query_fails(self, client):
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value.execute.side_effect = Exception("db down")
        with patch("focus_groups.api.get_pool_conn", return_value=mock_conn), \
             patch("focus_groups.api.return_pool_conn"):
            resp = client.get("/ready")
        assert resp.status_code == 503

    def test_no_auth_required(self, client):
        """Ready endpoint must work without X-API-Key header."""
        mock_conn = MagicMock()
        with patch("focus_groups.api.get_pool_conn", return_value=mock_conn), \
             patch("focus_groups.api.return_pool_conn"):
            resp = client.get("/ready")
        assert resp.status_code == 200
```

## Files Touched
- `src/focus_groups/api.py` (add health endpoints, refactor to APIRouter)
- `tests/test_health.py` (new)
- `tests/test_api.py` (update route references if affected by router refactor)
- `tests/test_rate_limiting.py` (same)
- `tests/test_auth.py` (same, verify health routes skip auth)

## Migration Notes
- All API URLs remain the same (`/api/sessions`, etc.) — the `prefix="/api"` on the router handles this
- Frontend code needs zero changes
- Existing tests may need `app.dependency_overrides` adjustments since auth moves from app-level to router-level
