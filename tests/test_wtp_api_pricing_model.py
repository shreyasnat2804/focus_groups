"""
API-level tests for WTP pricing model variants.

Tests the /api/sessions/{id}/wtp endpoint with different pricing models.
All Claude API calls and DB connections are mocked.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from focus_groups.personas.cards import PersonaCard


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_session():
    return {
        "session_id": "test-123",
        "question": "A project management SaaS tool",
        "sector": "tech",
        "num_personas": 2,
        "status": "completed",
        "demographic_filter": {},
        "responses": [
            {"post_id": 1, "response_text": "I think it's great."},
            {"post_id": 2, "response_text": "Could be cheaper."},
        ],
    }


@pytest.fixture
def sample_posts():
    return [
        {
            "post_id": 1,
            "demographic_tags": {"age_group": "25-34", "income_bracket": "high_income"},
            "text": "I work in fintech and spend a lot on SaaS tools.",
            "sector": "tech",
        },
        {
            "post_id": 2,
            "demographic_tags": {"age_group": "35-44", "income_bracket": "middle_income"},
            "text": "Budget-conscious, always comparing prices.",
            "sector": "tech",
        },
    ]


def _mock_claude_responses(psm_responses, demand_responses):
    """Build a mock client that returns PSM then demand responses in order."""
    client = MagicMock()
    all_responses = []
    for resp in psm_responses + demand_responses:
        message = MagicMock()
        message.content = [MagicMock(text=json.dumps(resp))]
        all_responses.append(message)
    client.messages.create.side_effect = all_responses
    return client


@pytest.fixture
def psm_responses():
    return [
        {"too_cheap": 20, "cheap": 50, "expensive": 150, "too_expensive": 300},
        {"too_cheap": 30, "cheap": 60, "expensive": 120, "too_expensive": 250},
    ]


@pytest.fixture
def demand_responses():
    """Default demand responses for derived price points."""
    # These are generic — the actual price keys depend on derived points
    return [
        {"50": True, "75": True, "100": True, "125": False, "150": False, "175": False, "200": False},
        {"50": True, "75": True, "100": False, "125": False, "150": False, "175": False, "200": False},
    ]


# ── Tests ────────────────────────────────────────────────────────────────────

class TestWtpPricingModel:
    """Tests for pricing model variants in the WTP endpoint."""

    @patch("focus_groups.api.get_session")
    @patch("focus_groups.api.get_posts_by_ids")
    @patch("focus_groups.api.get_client")
    def test_one_time_default(
        self, mock_get_client, mock_get_posts, mock_get_session,
        sample_session, sample_posts, psm_responses, demand_responses,
    ):
        """Omitting pricing_model should default to one_time."""
        from focus_groups.api import app, get_db

        mock_get_session.return_value = sample_session
        mock_get_posts.return_value = sample_posts
        mock_get_client.return_value = _mock_claude_responses(psm_responses, demand_responses)

        app.dependency_overrides[get_db] = lambda: MagicMock()
        client = TestClient(app)

        resp = client.post("/api/sessions/test-123/wtp", json={
            "segment_by": "income_bracket",
        })

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["pricing_model"] == "one_time"

    @patch("focus_groups.api.get_session")
    @patch("focus_groups.api.get_posts_by_ids")
    @patch("focus_groups.api.get_client")
    def test_subscription_request(
        self, mock_get_client, mock_get_posts, mock_get_session,
        sample_session, sample_posts, psm_responses, demand_responses,
    ):
        """Subscription model should be accepted and returned in response."""
        from focus_groups.api import app, get_db

        mock_get_session.return_value = sample_session
        mock_get_posts.return_value = sample_posts
        mock_get_client.return_value = _mock_claude_responses(psm_responses, demand_responses)

        app.dependency_overrides[get_db] = lambda: MagicMock()
        client = TestClient(app)

        resp = client.post("/api/sessions/test-123/wtp", json={
            "pricing_model": "subscription",
            "segment_by": "income_bracket",
        })

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["pricing_model"] == "subscription"

    def test_hybrid_missing_fields(self):
        """Hybrid model should 422 if upfront/subscription price points missing."""
        from focus_groups.api import app, get_db
        app.dependency_overrides[get_db] = lambda: MagicMock()
        client = TestClient(app)

        resp = client.post("/api/sessions/test-123/wtp", json={
            "pricing_model": "hybrid",
            "segment_by": "income_bracket",
        })

        app.dependency_overrides.clear()
        assert resp.status_code == 422

    @patch("focus_groups.api.get_session")
    @patch("focus_groups.api.get_posts_by_ids")
    @patch("focus_groups.api.get_client")
    def test_hybrid_response_shape(
        self, mock_get_client, mock_get_posts, mock_get_session,
        sample_session, sample_posts, psm_responses,
    ):
        """Hybrid response should have hybrid_tiers and normalized_price_points."""
        from focus_groups.api import app, get_db

        # For hybrid, demand responses use total_12m as keys
        # 500 + 49*12 = 1088, 500 + 99*12 = 1688
        demand_responses = [
            {"1088": True, "1688": False},
            {"1088": True, "1688": False},
        ]

        mock_get_session.return_value = sample_session
        mock_get_posts.return_value = sample_posts
        mock_get_client.return_value = _mock_claude_responses(psm_responses, demand_responses)

        app.dependency_overrides[get_db] = lambda: MagicMock()
        client = TestClient(app)

        resp = client.post("/api/sessions/test-123/wtp", json={
            "pricing_model": "hybrid",
            "upfront_price_points": [500],
            "subscription_price_points": [49, 99],
            "segment_by": "income_bracket",
        })

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["pricing_model"] == "hybrid"
        assert "hybrid_tiers" in data
        assert "normalized_price_points" in data
        assert len(data["hybrid_tiers"]) == 2  # 1 upfront x 2 sub

    @patch("focus_groups.api.get_session")
    @patch("focus_groups.api.get_posts_by_ids")
    @patch("focus_groups.api.get_client")
    def test_hybrid_normalized_totals_sorted(
        self, mock_get_client, mock_get_posts, mock_get_session,
        sample_session, sample_posts, psm_responses,
    ):
        """normalized_price_points should be in ascending order."""
        from focus_groups.api import app, get_db

        # 500+49*12=1088, 500+99*12=1688, 1000+49*12=1588, 1000+99*12=2188
        demand_responses = [
            {"1088": True, "1588": True, "1688": False, "2188": False},
            {"1088": True, "1588": False, "1688": False, "2188": False},
        ]

        mock_get_session.return_value = sample_session
        mock_get_posts.return_value = sample_posts
        mock_get_client.return_value = _mock_claude_responses(psm_responses, demand_responses)

        app.dependency_overrides[get_db] = lambda: MagicMock()
        client = TestClient(app)

        resp = client.post("/api/sessions/test-123/wtp", json={
            "pricing_model": "hybrid",
            "upfront_price_points": [500, 1000],
            "subscription_price_points": [49, 99],
            "segment_by": "income_bracket",
        })

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        normalized = data["normalized_price_points"]
        assert normalized == sorted(normalized)
