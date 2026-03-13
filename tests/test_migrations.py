"""Tests for the database migration framework."""

import os
import re
import stat
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = ROOT / "db" / "migrations"
MIGRATE_SCRIPT = ROOT / "db" / "migrate.sh"


class TestMigrateScript:
    """Tests for db/migrate.sh."""

    def test_migrate_script_exists(self):
        assert MIGRATE_SCRIPT.exists(), "db/migrate.sh does not exist"

    def test_migrate_script_is_executable(self):
        mode = MIGRATE_SCRIPT.stat().st_mode
        assert mode & stat.S_IXUSR, "db/migrate.sh is not executable by owner"

    def test_migrate_script_has_shebang(self):
        first_line = MIGRATE_SCRIPT.read_text().splitlines()[0]
        assert first_line.startswith("#!"), "db/migrate.sh missing shebang line"
        assert "bash" in first_line, "db/migrate.sh shebang should reference bash"

    def test_migrate_script_creates_schema_migrations_table(self):
        content = MIGRATE_SCRIPT.read_text()
        assert "schema_migrations" in content, (
            "migrate.sh should reference schema_migrations table"
        )
        assert "CREATE TABLE IF NOT EXISTS schema_migrations" in content


class TestMigrationFileNaming:
    """Tests for migration file naming and sequential numbering."""

    def _get_migration_files(self):
        """Return sorted list of .sql migration files (excluding README etc)."""
        return sorted(
            f for f in MIGRATIONS_DIR.iterdir()
            if f.suffix == ".sql" and re.match(r"^\d{3}_", f.name)
        )

    def test_migrations_directory_exists(self):
        assert MIGRATIONS_DIR.is_dir(), "db/migrations/ directory does not exist"

    def test_migration_files_follow_naming_convention(self):
        pattern = re.compile(r"^\d{3}_[a-z][a-z0-9_]*\.sql$")
        for f in self._get_migration_files():
            assert pattern.match(f.name), (
                f"Migration file '{f.name}' does not match NNN_snake_case.sql pattern"
            )

    def test_migration_numbers_are_sequential(self):
        files = self._get_migration_files()
        # Extract unique version numbers (there may be variant files like 002 and 002_apply_live)
        versions = sorted({int(f.name[:3]) for f in files})
        assert len(versions) >= 1, "Expected at least one migration file"
        # Check that no gaps exist in the sequence
        expected = list(range(versions[0], versions[-1] + 1))
        assert versions == expected, (
            f"Migration version numbers have gaps: {versions} vs expected {expected}"
        )

    def test_001_migration_exists(self):
        files = [f for f in self._get_migration_files() if f.name.startswith("001_")]
        assert len(files) == 1, "Expected exactly one 001_*.sql migration file"


class TestMigrationFileContent:
    """Tests that each migration file contains valid-looking SQL."""

    def _get_migration_files(self):
        return sorted(
            f for f in MIGRATIONS_DIR.iterdir()
            if f.suffix == ".sql" and re.match(r"^\d{3}_", f.name)
        )

    def test_each_migration_is_nonempty(self):
        for f in self._get_migration_files():
            content = f.read_text().strip()
            assert len(content) > 0, f"{f.name} is empty"

    def test_each_migration_contains_sql_keywords(self):
        sql_keywords = {"CREATE", "ALTER", "INSERT", "UPDATE", "DELETE", "DROP", "BEGIN"}
        for f in self._get_migration_files():
            content = f.read_text().upper()
            found = [kw for kw in sql_keywords if kw in content]
            assert found, (
                f"{f.name} does not contain any recognizable SQL keywords "
                f"({', '.join(sorted(sql_keywords))})"
            )

    def test_each_migration_has_comment_header(self):
        for f in self._get_migration_files():
            first_line = f.read_text().splitlines()[0]
            assert first_line.startswith("--"), (
                f"{f.name} should start with a SQL comment (--) describing the migration"
            )


class TestMigration001Content:
    """Tests specific to the 001_add_soft_delete_and_name migration."""

    @pytest.fixture()
    def migration_content(self):
        path = MIGRATIONS_DIR / "001_add_soft_delete_and_name.sql"
        return path.read_text()

    def test_adds_deleted_at_column(self, migration_content):
        assert "deleted_at" in migration_content, (
            "001 migration should add a deleted_at column"
        )
        assert "TIMESTAMPTZ" in migration_content.upper(), (
            "deleted_at should be TIMESTAMPTZ type"
        )

    def test_adds_name_column(self, migration_content):
        # Check for 'name' in a column-addition context
        assert re.search(r"ADD\s+COLUMN.*\bname\b", migration_content, re.IGNORECASE), (
            "001 migration should ADD COLUMN name"
        )

    def test_targets_focus_group_sessions(self, migration_content):
        assert "focus_group_sessions" in migration_content, (
            "001 migration should target focus_group_sessions table"
        )

    def test_uses_if_not_exists(self, migration_content):
        assert "IF NOT EXISTS" in migration_content.upper(), (
            "001 migration should use IF NOT EXISTS for idempotency"
        )

    def test_wrapped_in_transaction(self, migration_content):
        upper = migration_content.upper()
        assert "BEGIN" in upper, "001 migration should BEGIN a transaction"
        assert "COMMIT" in upper, "001 migration should COMMIT the transaction"

    def test_creates_index_on_deleted_at(self, migration_content):
        assert "idx_sessions_deleted_at" in migration_content, (
            "001 migration should create an index on deleted_at"
        )
