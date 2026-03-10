# 01 — Backend Dockerfile (FastAPI)

## Location

`Dockerfile` at project root (uses `src/` as the package source).

## Dockerfile Plan

```dockerfile
# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps for psycopg2-binary, numpy wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime-only deps (libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app source (needed for prompts/instructions.txt and any runtime file reads)
COPY src/ src/

# Non-root user
RUN useradd -r -s /bin/false appuser
USER appuser

EXPOSE 8080

# gunicorn with uvicorn workers
CMD ["gunicorn", "focus_groups.api:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-b", "0.0.0.0:8080", \
     "-w", "2", \
     "--timeout", "120", \
     "--access-logfile", "-"]
```

## Key Decisions

### Why gunicorn + uvicorn workers (not bare uvicorn)

- gunicorn handles process management, graceful restarts, worker recycling.
- Cloud Run can send concurrent requests to a single container — multiple workers handle that.
- `--timeout 120` accommodates Claude API calls which can be slow.

### Why multi-stage build

- Builder stage has gcc/build tools (~200MB). Runtime stage only has libpq5 (~5MB).
- Final image is ~300MB instead of ~700MB.

### Why `sentence-transformers` is a concern

- `sentence-transformers` pulls PyTorch (~2GB). The backend API **does not use it at runtime** — embeddings are pre-computed offline.
- **Action**: Split `requirements.txt` into two files:
  - `requirements.txt` — API runtime deps only (fastapi, uvicorn, psycopg2-binary, anthropic, etc.)
  - `requirements-ml.txt` — offline/batch deps (sentence-transformers, torch)
- This keeps the backend image under 400MB instead of 2.5GB.

### Requirements split

**requirements.txt** (API runtime — goes into Dockerfile):
```
psycopg2-binary>=2.9
python-dotenv>=1.0
pgvector>=0.3
numpy>=1.24
anthropic>=0.40
fastapi>=0.115
uvicorn>=0.30
fpdf2>=2.7
slowapi>=0.1.9
matplotlib>=3.8
gunicorn>=22.0
```

**requirements-ml.txt** (offline jobs only):
```
-r requirements.txt
sentence-transformers>=3.0
requests>=2.32
```

### .dockerignore

```
.venv/
.git/
.claude/
__pycache__/
*.pyc
.env
tests/
plans/
frontend/
node_modules/
*.egg-info/
```

## Health Checks

Already implemented in `api.py`:
- `GET /health` — liveness (process alive)
- `GET /ready` — readiness (DB pool reachable)

Cloud Run uses these via startup/liveness probes configured at deploy time.

## Environment Variables Required

| Var | Source | Notes |
|-----|--------|-------|
| `PG_HOST` | Cloud SQL proxy Unix socket path | e.g. `/cloudsql/project:region:instance` |
| `PG_PORT` | Not needed with Unix socket | Omit or leave default |
| `PG_DB` | `focusgroups` | Same as local |
| `PG_USER` | Secret Manager | |
| `PG_PASSWORD` | Secret Manager | |
| `ANTHROPIC_API_KEY` | Secret Manager | |
| `FG_API_KEY` | Secret Manager | API auth key |
| `CORS_ORIGINS` | Cloud Run env var | Frontend URL |
| `LOG_FORMAT` | `json` | Already defaults to json |
| `PORT` | Cloud Run sets automatically | 8080 |

## Testing the Image Locally

```bash
docker build -t fg-api .
docker run --rm -p 8080:8080 --env-file .env fg-api

# Verify
curl http://localhost:8080/health
curl http://localhost:8080/ready
```
