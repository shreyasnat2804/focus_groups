"""
Security regression tests.

Covers SQL injection, CSV injection, Content-Disposition header injection,
input validation boundaries, and Unicode edge cases.
"""

import csv
import io
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Return a TestClient with all external deps mocked."""
    mock_conn = MagicMock()

    with (
        patch("focus_groups.api.get_client") as mock_get_client,
        patch("focus_groups.api.select_personas") as mock_select,
        patch("focus_groups.api.run_focus_group") as mock_run,
        patch("focus_groups.api.create_session") as mock_create,
        patch("focus_groups.api.save_responses"),
        patch("focus_groups.api.complete_session"),
        patch("focus_groups.api.fail_session"),
        patch("focus_groups.api.get_session") as mock_get_session,
        patch("focus_groups.api.list_sessions") as mock_list,
        patch("focus_groups.api.count_sessions") as mock_count,
        patch("focus_groups.api.update_session_question"),
        patch("focus_groups.api.update_session_name"),
        patch("focus_groups.api.delete_responses"),
        patch("focus_groups.api.purge_expired_sessions"),
    ):
        mock_get_client.return_value = MagicMock()
        mock_select.return_value = [MagicMock()]
        mock_run.return_value = [
            {
                "post_id": 1,
                "persona_summary": "test",
                "system_prompt": "test",
                "response_text": "test",
                "model": "test",
            }
        ]
        mock_create.return_value = "test-session-id"
        mock_count.return_value = 5
        mock_list.return_value = []
        mock_get_session.return_value = {
            "id": "test-session-id",
            "sector": "tech",
            "demographic_filter": {},
            "question": "old question",
            "num_personas": 5,
            "status": "completed",
            "created_at": "2026-01-01",
            "completed_at": "2026-01-01",
            "name": None,
            "responses": [
                {
                    "id": 1,
                    "post_id": 1,
                    "persona_summary": "test persona",
                    "response_text": "test response",
                    "model": "test-model",
                    "created_at": "2026-01-01",
                }
            ],
        }

        from focus_groups.api import app, get_db

        app.dependency_overrides[get_db] = lambda: mock_conn
        app.state.limiter.reset()
        yield TestClient(app)
        app.dependency_overrides.clear()


HEADERS = {"X-API-Key": "test-key"}


# ── SQL Injection Tests ──────────────────────────────────────────────────────

class TestSqlInjection:
    """Verify _build_filter_clause uses parameterized queries against SQL injection."""

    SQL_PAYLOADS = [
        "'; DROP TABLE focus_group_sessions; --",
        "' OR '1'='1",
        "' UNION SELECT * FROM posts --",
        "%' OR 1=1 --",
        "'; DELETE FROM focus_group_sessions WHERE '1'='1",
    ]

    def test_build_filter_clause_parameterises_search(self):
        """Search values must land in the params list, never interpolated into SQL."""
        from focus_groups.sessions import _build_filter_clause

        for payload in self.SQL_PAYLOADS:
            where, params = _build_filter_clause(search=payload)
            # The payload should be inside the params (as a LIKE pattern), not in the WHERE text
            assert payload not in where, f"Payload leaked into WHERE clause: {payload}"
            assert len(params) >= 1
            # The param wraps the (escaped) value in %...%
            assert params[0].startswith("%")
            assert params[0].endswith("%")

    def test_build_filter_clause_parameterises_sector(self):
        from focus_groups.sessions import _build_filter_clause

        for payload in self.SQL_PAYLOADS:
            where, params = _build_filter_clause(sector=payload)
            assert payload not in where
            assert payload in params

    def test_build_filter_clause_uses_placeholders(self):
        """WHERE clause must only contain %s placeholders, never raw values."""
        from focus_groups.sessions import _build_filter_clause

        where, params = _build_filter_clause(
            search="'; DROP TABLE x; --", sector="' OR 1=1 --"
        )
        # Only %s placeholders should appear for user-supplied values
        assert where.count("%s") == len(params)

    def test_list_sessions_endpoint_with_sql_injection_search(self, client):
        """SQL injection payloads in ?search= must not cause server errors."""
        for payload in self.SQL_PAYLOADS:
            resp = client.get(
                "/api/sessions",
                params={"search": payload},
                headers=HEADERS,
            )
            # Should succeed (returning empty results), not 500
            assert resp.status_code == 200, f"Payload caused error: {payload}"


# ── CSV Injection Tests ──────────────────────────────────────────────────────

class TestCsvInjection:
    """Verify export_csv sanitises formula-triggering characters."""

    FORMULA_PAYLOADS = [
        "=cmd|'/C calc'!A0",
        "+cmd|'/C calc'!A0",
        "-cmd|'/C calc'!A0",
        "@SUM(1+1)*cmd|'/C calc'!A0",
        '=HYPERLINK("http://evil.com","click")',
    ]

    def _make_session(self, persona_summary: str, response_text: str) -> dict:
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
                    "persona_summary": persona_summary,
                    "response_text": response_text,
                    "model": "test-model",
                    "created_at": now,
                },
            ],
        }

    def _parse_csv_data_rows(self, csv_text: str) -> list[list[str]]:
        lines = [l for l in csv_text.strip().split("\n") if not l.startswith("#")]
        reader = csv.reader(io.StringIO("\n".join(lines)))
        rows = list(reader)
        return rows[1:]  # skip header

    def test_persona_summary_payloads_sanitised(self):
        from focus_groups.export import export_csv

        for payload in self.FORMULA_PAYLOADS:
            session = self._make_session(persona_summary=payload, response_text="safe")
            csv_text = export_csv(session)
            rows = self._parse_csv_data_rows(csv_text)
            assert rows[0][2].startswith("'"), (
                f"persona_summary not prefixed for: {payload}"
            )

    def test_response_text_payloads_sanitised(self):
        from focus_groups.export import export_csv

        for payload in self.FORMULA_PAYLOADS:
            session = self._make_session(persona_summary="safe", response_text=payload)
            csv_text = export_csv(session)
            rows = self._parse_csv_data_rows(csv_text)
            assert rows[0][3].startswith("'"), (
                f"response_text not prefixed for: {payload}"
            )

    def test_safe_values_not_modified(self):
        from focus_groups.export import export_csv

        session = self._make_session(
            persona_summary="Normal persona", response_text="Normal response"
        )
        csv_text = export_csv(session)
        rows = self._parse_csv_data_rows(csv_text)
        assert rows[0][2] == "Normal persona"
        assert rows[0][3] == "Normal response"


# ── Content-Disposition Header Injection ─────────────────────────────────────

class TestContentDispositionInjection:
    """Verify session IDs with CRLF or special chars cannot inject headers."""

    def test_safe_filename_strips_crlf(self):
        from focus_groups.api import _safe_filename

        result = _safe_filename("abc\r\nContent-Type: text/html")
        assert "\r" not in result
        assert "\n" not in result
        # Colons and spaces are also stripped, so no valid header injection possible
        assert ":" not in result
        assert " " not in result

    def test_safe_filename_strips_url_encoded_crlf(self):
        from focus_groups.api import _safe_filename

        result = _safe_filename("abc%0d%0aContent-Type: text/html")
        assert "%" not in result
        assert " " not in result

    def test_safe_filename_strips_path_traversal(self):
        from focus_groups.api import _safe_filename

        result = _safe_filename("../../../etc/passwd")
        assert "/" not in result
        assert ".." not in result

    def test_export_csv_endpoint_sanitises_session_id(self, client):
        """The CSV export endpoint must not reflect unsanitised session IDs in headers."""
        resp = client.get(
            "/api/sessions/test-session-id/export/csv",
            headers=HEADERS,
        )
        assert resp.status_code == 200
        cd = resp.headers["content-disposition"]
        assert "\r" not in cd
        assert "\n" not in cd

    def test_export_pdf_endpoint_sanitises_session_id(self, client):
        """The PDF export endpoint must not reflect unsanitised session IDs in headers."""
        resp = client.get(
            "/api/sessions/test-session-id/export/pdf",
            headers=HEADERS,
        )
        assert resp.status_code == 200
        cd = resp.headers["content-disposition"]
        assert "\r" not in cd
        assert "\n" not in cd


# ── Input Validation Boundary Tests ──────────────────────────────────────────

class TestInputValidationBoundaries:
    """Test Pydantic models at exact boundaries."""

    def test_num_personas_exactly_one_accepted(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "Test?", "num_personas": 1},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_num_personas_exactly_fifty_accepted(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "Test?", "num_personas": 50},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_num_personas_fifty_one_rejected(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "Test?", "num_personas": 51},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_num_personas_zero_rejected(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "Test?", "num_personas": 0},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_question_at_exact_max_length_accepted(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "x" * 2000, "num_personas": 5},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_question_one_over_max_rejected(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "x" * 2001, "num_personas": 5},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_empty_question_rejected(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "", "num_personas": 5},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_invalid_sector_rejected(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "Test?", "num_personas": 5, "sector": "invalid"},
            headers=HEADERS,
        )
        assert resp.status_code == 422

    def test_deeply_nested_demographic_filter_accepted(self, client):
        """Deeply nested dicts in demographic_filter should not crash the server."""
        deep = {"level1": {"level2": {"level3": {"level4": "value"}}}}
        resp = client.post(
            "/api/sessions",
            json={"question": "Test?", "num_personas": 5, "demographic_filter": deep},
            headers=HEADERS,
        )
        # Should not 500 — either accepted or rejected cleanly
        assert resp.status_code in (200, 422)


# ── Special Character / Unicode Edge Cases ───────────────────────────────────

class TestSpecialCharacters:
    """Test Unicode edge cases in question/response fields."""

    def test_null_byte_in_search(self, client):
        """Null bytes in search should not cause server errors."""
        resp = client.get(
            "/api/sessions",
            params={"search": "test\x00value"},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_unicode_bom_in_question(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "\ufeffWhat do you think?", "num_personas": 5},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_rtl_override_in_question(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "\u202eWhat do you think?", "num_personas": 5},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_long_question_just_under_limit(self, client):
        resp = client.post(
            "/api/sessions",
            json={"question": "x" * 1999, "num_personas": 5},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_csv_export_with_unicode_in_response(self):
        """Unicode characters in responses must not break CSV export."""
        from focus_groups.export import export_csv

        now = datetime.now(timezone.utc)
        session = {
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
                    "persona_summary": "Persona with \u202e RTL and \ufeff BOM",
                    "response_text": "Response with null\x00byte",
                    "model": "test-model",
                    "created_at": now,
                },
            ],
        }
        csv_text = export_csv(session)
        # Must produce valid CSV (no exceptions) with content
        assert len(csv_text) > 0
        lines = [l for l in csv_text.strip().split("\n") if not l.startswith("#")]
        reader = csv.reader(io.StringIO("\n".join(lines)))
        rows = list(reader)
        assert len(rows) == 2  # header + 1 data row

    def test_sanitize_csv_value_with_null_byte(self):
        """Null byte should not trigger formula sanitisation (it's not =+-@)."""
        from focus_groups.export import _sanitize_csv_value

        assert _sanitize_csv_value("\x00test") == "\x00test"
