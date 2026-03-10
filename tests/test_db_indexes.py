"""
Tests for database indexes from plans/db_indexes_plan.md.

1. Unit test: migration SQL file exists and contains the expected CREATE INDEX statements.
2. Integration tests (require Docker Postgres): verify the indexes exist after applying the migration.

Run with: python3 -m pytest tests/test_db_indexes.py -v
"""

import os
import pathlib

import pytest

from focus_groups.db import get_conn

MIGRATION_FILE = pathlib.Path(__file__).resolve().parents[1] / "db" / "migrations" / "006_add_indexes.sql"

EXPECTED_INDEXES = [
    "idx_posts_author",
    "idx_posts_sector",
    "idx_sessions_created_at",
]

# Also covered in migration 004, but referenced in the plan
EXPECTED_FROM_004 = "idx_sessions_deleted_at"


# ---------------------------------------------------------------------------
# Unit: migration file correctness
# ---------------------------------------------------------------------------

def test_migration_file_exists():
    """The migration SQL file must exist."""
    assert MIGRATION_FILE.exists(), f"Missing migration file: {MIGRATION_FILE}"


def test_migration_contains_expected_indexes():
    """The migration file must reference all planned indexes."""
    sql = MIGRATION_FILE.read_text()
    for idx_name in EXPECTED_INDEXES:
        assert idx_name in sql, f"Migration missing CREATE INDEX for {idx_name}"


def test_migration_uses_if_not_exists():
    """All CREATE INDEX statements must use IF NOT EXISTS for safe re-runs."""
    sql = MIGRATION_FILE.read_text()
    for line in sql.splitlines():
        if line.strip().upper().startswith("CREATE INDEX"):
            assert "IF NOT EXISTS" in line.upper(), (
                f"CREATE INDEX without IF NOT EXISTS: {line.strip()}"
            )


def test_migration_wrapped_in_transaction():
    """Migration should be wrapped in BEGIN/COMMIT."""
    sql = MIGRATION_FILE.read_text().upper()
    assert "BEGIN" in sql
    assert "COMMIT" in sql


# ---------------------------------------------------------------------------
# Integration: verify indexes exist in the database
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def conn():
    """Single DB connection for the module. Skip if DB unreachable."""
    try:
        c = get_conn()
        # Apply the migration so indexes exist
        with c.cursor() as cur:
            cur.execute(MIGRATION_FILE.read_text())
        c.commit()
        yield c
        c.close()
    except Exception as exc:
        pytest.skip(f"Postgres not available: {exc}")


def _index_exists(conn, index_name: str) -> bool:
    """Check whether a given index exists in the database."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_indexes WHERE indexname = %s",
            (index_name,),
        )
        return cur.fetchone() is not None


@pytest.mark.parametrize("index_name", EXPECTED_INDEXES + [EXPECTED_FROM_004])
def test_index_exists_in_database(conn, index_name):
    """Each planned index must exist after applying migrations."""
    assert _index_exists(conn, index_name), f"Index {index_name} not found in database"
