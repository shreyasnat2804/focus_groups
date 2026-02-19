#!/usr/bin/env bash
# Stage 1 verification — run from project root:
#   bash scripts/run_stage1.sh
set -euo pipefail

PYTHON=".venv/bin/python"

echo "=== Stage 1: Data Pipeline & Infrastructure ==="
echo

# 1. Unit tests (no DB needed)
echo "--- [1/6] Running unit tests ---"
$PYTHON -m pytest tests/test_tagger.py -v
echo

# 2. Start Docker Postgres
echo "--- [2/6] Starting Docker Postgres ---"
docker compose up -d
echo "Waiting 5s for Postgres to be ready..."
sleep 5
echo

# 3. Apply unique index migration
echo "--- [3/6] Applying schema migration ---"
$PYTHON scripts/migrate_tags_unique_index.py
echo

# 4. Tag existing posts
echo "--- [4/6] Tagging existing posts ---"
$PYTHON scripts/tag_existing.py
echo

# 5. Quality report
echo "--- [5/6] Quality report ---"
$PYTHON scripts/quality_report.py
echo

# 6. Export CSV
echo "--- [6/6] Exporting CSV ---"
$PYTHON scripts/export_csv.py
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
