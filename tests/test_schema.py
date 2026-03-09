"""Tests that db/init.sql schema matches what the application code expects."""

import re
from pathlib import Path

INIT_SQL = Path(__file__).parent.parent / "db" / "init.sql"


def _read_init_sql() -> str:
    return INIT_SQL.read_text()


def _extract_create_table(sql: str, table_name: str) -> str:
    """Extract the CREATE TABLE block for a given table name."""
    pattern = rf"CREATE TABLE IF NOT EXISTS {table_name}\s*\((.*?)\);"
    match = re.search(pattern, sql, re.DOTALL)
    assert match, f"CREATE TABLE for {table_name} not found in init.sql"
    return match.group(1)


class TestFocusGroupSessionsSchema:
    """Ensure focus_group_sessions has all columns the app expects."""

    def setup_method(self):
        self.sql = _read_init_sql()
        self.table_def = _extract_create_table(self.sql, "focus_group_sessions")

    def test_has_deleted_at_column(self):
        assert "deleted_at" in self.table_def, (
            "focus_group_sessions must have a deleted_at column for soft deletes"
        )

    def test_deleted_at_is_nullable_timestamptz(self):
        # Should be TIMESTAMPTZ and nullable (no NOT NULL)
        line = [l.strip() for l in self.table_def.split("\n") if "deleted_at" in l]
        assert line, "deleted_at column not found"
        col_def = line[0]
        assert "TIMESTAMPTZ" in col_def.upper()
        assert "NOT NULL" not in col_def.upper(), "deleted_at must be nullable"

    def test_has_name_column(self):
        assert "name" in self.table_def, (
            "focus_group_sessions must have a name column for session display names"
        )

    def test_name_is_nullable(self):
        # name column should exist and be nullable
        lines = [l.strip() for l in self.table_def.split("\n") if "name" in l.lower()]
        # Filter to just the 'name' column definition (not 'table_name' etc.)
        name_lines = [l for l in lines if re.match(r"name\s+", l)]
        assert name_lines, "name column not found"
        assert "NOT NULL" not in name_lines[0].upper(), "name must be nullable"

    def test_has_all_expected_columns(self):
        """Verify all columns expected by sessions.py are present."""
        expected = [
            "id", "sector", "demographic_filter", "question",
            "num_personas", "status", "created_at", "completed_at",
            "deleted_at", "name",
        ]
        for col in expected:
            assert col in self.table_def, f"Column {col} missing from focus_group_sessions"
