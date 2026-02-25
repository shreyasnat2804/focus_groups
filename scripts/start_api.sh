#!/usr/bin/env bash
# Start the full stack: Colima → Postgres → Data pipeline → FastAPI
# Usage: bash scripts/start_api.sh [--skip-scrape]
set -euo pipefail

PYTHON=".venv/bin/python"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

SKIP_SCRAPE=false
for arg in "$@"; do
    case "$arg" in
        --skip-scrape) SKIP_SCRAPE=true ;;
        *) echo "Unknown flag: $arg (use --skip-scrape to skip Reddit fetch)" >&2; exit 1 ;;
    esac
done

# ── 0. Point Docker CLI at Colima's socket ───────────────────────────────────
export DOCKER_HOST="unix://${HOME}/.colima/default/docker.sock"

# ── 1. Start Colima (Docker runtime) ─────────────────────────────────────────
echo "--- [1/7] Starting Colima ---"
if colima status &>/dev/null; then
    echo "Colima already running."
else
    colima start
    echo "Colima started."
fi

# ── 2. Start Postgres via Docker Compose ─────────────────────────────────────
echo "--- [2/7] Starting Postgres ---"
if docker ps --format '{{.Names}}' | grep -q fg_postgres; then
    echo "fg_postgres already running."
else
    docker compose up -d
    echo "Waiting for Postgres to be ready..."
    for i in $(seq 1 15); do
        if docker exec fg_postgres pg_isready -U fg_user -d focusgroups &>/dev/null; then
            echo "Postgres ready."
            break
        fi
        if [ "$i" -eq 15 ]; then
            echo "ERROR: Postgres did not become ready in time."
            exit 1
        fi
        sleep 1
    done
fi

# ── 3. Verify DB connection ──────────────────────────────────────────────────
echo "--- [3/7] Verifying DB connection ---"
$PYTHON -c "from focus_groups.db import get_conn; get_conn().close(); print('DB connection OK')"

# ── 4. Scrape newest Reddit posts ────────────────────────────────────────────
if [ "$SKIP_SCRAPE" = true ]; then
    echo "--- [4/7] Scraping Reddit (skipped via --skip-scrape) ---"
else
    echo "--- [4/7] Scraping newest Reddit posts (probe mode — 1 page per sub) ---"
    $PYTHON -m focus_groups.scraper probe
fi

# ── 5. Load any JSONL data into Postgres ─────────────────────────────────────
echo "--- [5/7] Loading posts into DB ---"
$PYTHON scripts/load_jsonl.py

# ── 6. Tag & embed new posts ─────────────────────────────────────────────────
echo "--- [6/7] Tagging untagged posts ---"
$PYTHON scripts/tag_existing.py

echo "--- [7/7] Embedding unembedded posts ---"
$PYTHON scripts/generate_embeddings.py

# ── Done — start FastAPI ─────────────────────────────────────────────────────
echo
echo "=== Data pipeline complete ==="
echo "Starting FastAPI..."
echo "API: http://localhost:8000"
echo "Docs: http://localhost:8000/docs"
echo
$PYTHON -m uvicorn focus_groups.api:app --reload --port 8000
