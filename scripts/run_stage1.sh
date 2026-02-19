#!/usr/bin/env bash
# Stage 1 verification — run from project root:
#   bash scripts/run_stage1.sh        # summary output
#   bash scripts/run_stage1.sh -v     # verbose output
set -euo pipefail

PYTHON=".venv/bin/python"
VERBOSE=""

# Parse flags
for arg in "$@"; do
    case "$arg" in
        -v|--verbose) VERBOSE="-v" ;;
        *) echo "Unknown flag: $arg" >&2; exit 1 ;;
    esac
done

echo "=== Stage 1: Data Pipeline & Infrastructure ==="
[[ -n "$VERBOSE" ]] && echo "(verbose mode)"
echo

# 1. Unit tests (no DB needed)
echo "--- [1/6] Running unit tests ---"
$PYTHON -m pytest tests/test_tagger.py -v
echo

# 2. Ensure Postgres is reachable (Docker or native Homebrew)
echo "--- [2/6] Checking Postgres ---"
if command -v docker &>/dev/null; then
    echo "Docker found — starting via docker compose..."
    docker compose up -d
    echo "Waiting 5s for Postgres to be ready..."
    sleep 5
else
    echo "Docker not found — assuming native Postgres is running."
fi
# Fail fast if DB is unreachable
$PYTHON -c "from src.db import get_conn; get_conn().close(); print('DB connection OK')"
echo

# 3. Apply unique index migration
echo "--- [3/6] Applying schema migration ---"
$PYTHON scripts/migrate_tags_unique_index.py $VERBOSE
echo

# 4. Tag existing posts
echo "--- [4/6] Tagging existing posts ---"
$PYTHON scripts/tag_existing.py $VERBOSE
echo

# 5. Quality report
echo "--- [5/6] Quality report ---"
$PYTHON scripts/quality_report.py $VERBOSE
echo

# 6. Export CSV
echo "--- [6/6] Exporting CSV ---"
$PYTHON scripts/export_csv.py $VERBOSE
echo

# Verify output
if [[ -f data/posts_tagged.csv ]]; then
    lines=$(wc -l < data/posts_tagged.csv)
    echo "data/posts_tagged.csv exists — $lines lines (including header)"
else
    echo "WARNING: data/posts_tagged.csv not found"
fi

echo
echo "=== Stage 1 complete ==="
echo "Run the scraper (probe) to confirm inline tagging works:"
echo "  $PYTHON -m src.scraper probe"
