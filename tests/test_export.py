"""
Tests for src.export — CSV and PDF export of focus group sessions.

Unit tests with canned session dicts (no DB required).
"""

import csv
import io
from datetime import datetime, timezone

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_session():
    now = datetime.now(timezone.utc)
    return {
        "id": 1,
        "sector": "tech",
        "demographic_filter": {"age_group": "25-34"},
        "question": "What do you think about AI?",
        "num_personas": 2,
        "status": "completed",
        "created_at": now,
        "completed_at": now,
        "responses": [
            {
                "id": 1,
                "post_id": 42,
                "persona_summary": "25-34 year old male",
                "system_prompt": "You are simulating...",
                "response_text": "I think AI is great for productivity.",
                "model": "claude-sonnet-4-20250514",
                "created_at": now,
            },
            {
                "id": 2,
                "post_id": 43,
                "persona_summary": "35-44 year old female",
                "system_prompt": "You are simulating...",
                "response_text": "I'm worried about bias in hiring.",
                "model": "claude-sonnet-4-20250514",
                "created_at": now,
            },
        ],
    }


@pytest.fixture
def empty_session():
    now = datetime.now(timezone.utc)
    return {
        "id": 2,
        "sector": None,
        "demographic_filter": {},
        "question": "Empty test?",
        "num_personas": 5,
        "status": "completed",
        "created_at": now,
        "completed_at": now,
        "responses": [],
    }


# ── CSV tests ────────────────────────────────────────────────────────────────

def test_export_csv_basic(sample_session):
    from focus_groups.export import export_csv

    result = export_csv(sample_session)
    assert isinstance(result, str)

    # Should have header row + 2 data rows (comments don't count in csv reader)
    lines = [l for l in result.strip().split("\n") if not l.startswith("#")]
    reader = csv.reader(io.StringIO("\n".join(lines)))
    rows = list(reader)
    assert len(rows) == 3  # header + 2 data rows
    assert rows[0] == ["response_id", "post_id", "persona_summary", "response_text", "model"]


def test_export_csv_includes_metadata(sample_session):
    from focus_groups.export import export_csv

    result = export_csv(sample_session)
    # Comment header should include session metadata
    assert "# question: What do you think about AI?" in result
    assert "# sector: tech" in result
    assert "# status: completed" in result


def test_export_csv_response_data(sample_session):
    from focus_groups.export import export_csv

    result = export_csv(sample_session)
    lines = [l for l in result.strip().split("\n") if not l.startswith("#")]
    reader = csv.reader(io.StringIO("\n".join(lines)))
    rows = list(reader)

    assert rows[1][0] == "1"  # response_id
    assert rows[1][1] == "42"  # post_id
    assert rows[1][2] == "25-34 year old male"
    assert "AI is great" in rows[1][3]


def test_export_csv_empty_responses(empty_session):
    from focus_groups.export import export_csv

    result = export_csv(empty_session)
    lines = [l for l in result.strip().split("\n") if not l.startswith("#")]
    reader = csv.reader(io.StringIO("\n".join(lines)))
    rows = list(reader)
    assert len(rows) == 1  # header only


# ── PDF tests ────────────────────────────────────────────────────────────────

def test_export_pdf_returns_bytes(sample_session):
    from focus_groups.export import export_pdf

    result = export_pdf(sample_session)
    assert isinstance(result, bytes)
    assert result[:5] == b"%PDF-"


def test_export_pdf_has_content(sample_session):
    from focus_groups.export import export_pdf

    result = export_pdf(sample_session)
    # PDF with responses should be larger than empty PDF
    empty_session = {**sample_session, "responses": []}
    empty_result = export_pdf(empty_session)
    assert len(result) > len(empty_result)


def test_export_pdf_empty_responses(empty_session):
    from focus_groups.export import export_pdf

    result = export_pdf(empty_session)
    assert isinstance(result, bytes)
    assert result[:5] == b"%PDF-"
