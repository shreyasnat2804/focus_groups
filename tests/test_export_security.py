"""
Tests for export security hardening.

Covers CSV formula injection protection and Content-Disposition filename sanitization.
"""

import csv
import io
from datetime import datetime, timezone

import pytest


# ── _sanitize_csv_value tests ────────────────────────────────────────────────

class TestSanitizeCsvValue:
    def test_equals_sign_prefixed(self):
        from focus_groups.export import _sanitize_csv_value
        assert _sanitize_csv_value("=cmd|'/C calc'!A0") == "'=cmd|'/C calc'!A0"

    def test_plus_sign_prefixed(self):
        from focus_groups.export import _sanitize_csv_value
        assert _sanitize_csv_value("+cmd|'/C calc'!A0") == "'+cmd|'/C calc'!A0"

    def test_minus_sign_prefixed(self):
        from focus_groups.export import _sanitize_csv_value
        assert _sanitize_csv_value("-1+1") == "'-1+1"

    def test_at_sign_prefixed(self):
        from focus_groups.export import _sanitize_csv_value
        assert _sanitize_csv_value("@SUM(A1:A10)") == "'@SUM(A1:A10)"

    def test_tab_prefixed(self):
        from focus_groups.export import _sanitize_csv_value
        assert _sanitize_csv_value("\tcmd") == "'\tcmd"

    def test_carriage_return_prefixed(self):
        from focus_groups.export import _sanitize_csv_value
        assert _sanitize_csv_value("\rcmd") == "'\rcmd"

    def test_safe_value_unchanged(self):
        from focus_groups.export import _sanitize_csv_value
        assert _sanitize_csv_value("Hello world") == "Hello world"

    def test_empty_string_unchanged(self):
        from focus_groups.export import _sanitize_csv_value
        assert _sanitize_csv_value("") == ""

    def test_numeric_string_unchanged(self):
        from focus_groups.export import _sanitize_csv_value
        assert _sanitize_csv_value("12345") == "12345"


# ── CSV export integration with sanitization ─────────────────────────────────

class TestCsvExportSanitization:
    @pytest.fixture
    def malicious_session(self):
        now = datetime.now(timezone.utc)
        return {
            "id": 1,
            "sector": "tech",
            "demographic_filter": {},
            "question": "Test?",
            "num_personas": 1,
            "status": "completed",
            "created_at": now,
            "completed_at": now,
            "responses": [
                {
                    "id": 1,
                    "post_id": 42,
                    "persona_summary": "=cmd|'/C calc'!A0",
                    "response_text": "+cmd|'/C calc'!A0",
                    "model": "claude-sonnet-4-20250514",
                    "created_at": now,
                },
            ],
        }

    def test_exported_csv_sanitizes_persona_summary(self, malicious_session):
        from focus_groups.export import export_csv

        result = export_csv(malicious_session)
        lines = [l for l in result.strip().split("\n") if not l.startswith("#")]
        reader = csv.reader(io.StringIO("\n".join(lines)))
        rows = list(reader)
        # persona_summary (col 2) should be prefixed with single quote
        assert rows[1][2].startswith("'")

    def test_exported_csv_sanitizes_response_text(self, malicious_session):
        from focus_groups.export import export_csv

        result = export_csv(malicious_session)
        lines = [l for l in result.strip().split("\n") if not l.startswith("#")]
        reader = csv.reader(io.StringIO("\n".join(lines)))
        rows = list(reader)
        # response_text (col 3) should be prefixed with single quote
        assert rows[1][3].startswith("'")


# ── _safe_filename tests ─────────────────────────────────────────────────────

class TestSafeFilename:
    def test_valid_uuid_unchanged(self):
        from focus_groups.api import _safe_filename
        assert _safe_filename("550e8400-e29b-41d4-a716-446655440000") == "550e8400-e29b-41d4-a716-446655440000"

    def test_strips_path_traversal(self):
        from focus_groups.api import _safe_filename
        assert _safe_filename("../../etc/passwd") == "etcpasswd"

    def test_strips_header_injection(self):
        from focus_groups.api import _safe_filename
        result = _safe_filename('foo\r\nX-Injected: true')
        assert "\r" not in result
        assert "\n" not in result

    def test_strips_special_chars(self):
        from focus_groups.api import _safe_filename
        assert _safe_filename("hello world!@#") == "helloworld"

    def test_empty_input(self):
        from focus_groups.api import _safe_filename
        assert _safe_filename("") == ""
