#!/usr/bin/env bash
# migrate.sh — Lightweight SQL migration runner for focus_groups.
#
# Applies numbered migration files from db/migrations/ in order,
# tracking which have been applied in a schema_migrations table.
#
# Usage:
#   db/migrate.sh              # apply all pending migrations
#   db/migrate.sh --dry-run    # show what would be applied without running
#
# Environment variables (with defaults):
#   PG_HOST=localhost  PG_PORT=5432  PG_USER=fg_user  PG_PASSWORD=  PG_DB=focusgroups

set -euo pipefail

MIGRATIONS_DIR="$(cd "$(dirname "$0")/migrations" && pwd)"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

# Connection defaults
: "${PG_HOST:=localhost}"
: "${PG_PORT:=5432}"
: "${PG_USER:=fg_user}"
: "${PG_PASSWORD:=}"
: "${PG_DB:=focusgroups}"

export PGPASSWORD="$PG_PASSWORD"

psql_cmd() {
    psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
        --no-psqlrc --quiet --tuples-only --no-align "$@"
}

# ── Ensure schema_migrations table exists ──────────────────────────────────────

psql_cmd -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    version   VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);
"

# ── Collect and apply pending migrations ───────────────────────────────────────

applied=0

for migration_file in "$MIGRATIONS_DIR"/[0-9][0-9][0-9]_*.sql; do
    [ -f "$migration_file" ] || continue

    filename="$(basename "$migration_file")"
    version="${filename%%_*}"  # e.g. "001"

    # Skip if already applied
    already=$(psql_cmd -c "SELECT 1 FROM schema_migrations WHERE version = '$version';")
    if [[ "$already" == "1" ]]; then
        continue
    fi

    if $DRY_RUN; then
        echo "[dry-run] Would apply: $filename"
        applied=$((applied + 1))
        continue
    fi

    echo "Applying migration: $filename ..."
    psql_cmd -f "$migration_file"

    psql_cmd -c "INSERT INTO schema_migrations (version) VALUES ('$version');"
    echo "  -> Applied $filename"
    applied=$((applied + 1))
done

if $DRY_RUN; then
    echo "$applied migration(s) would be applied."
else
    if [[ $applied -eq 0 ]]; then
        echo "No pending migrations."
    else
        echo "$applied migration(s) applied successfully."
    fi
fi
