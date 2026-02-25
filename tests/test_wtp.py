"""
Tests for WTP (Willingness to Pay) analysis module.

Covers:
- JSON extraction/parsing from Claude responses
- Van Westendorp Price Sensitivity Meter (PSM)
- Gabor-Granger demand simulation
- Segmented output by demographic dimension
- Visualization chart generation
- CLI entry point

All Claude API calls are mocked.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch, call

import pytest

from focus_groups.personas.cards import PersonaCard


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_cards():
    """Diverse set of persona cards for WTP testing."""
    return [
        PersonaCard(
            post_id=1,
            demographic_tags={"age_group": "25-34", "gender": "male", "income_bracket": "high_income"},
            text_excerpt="I work in fintech and spend a lot on SaaS tools.",
            sector="tech",
        ),
        PersonaCard(
            post_id=2,
            demographic_tags={"age_group": "35-44", "gender": "female", "income_bracket": "middle_income"},
            text_excerpt="Budget-conscious mom, always comparing prices.",
            sector="tech",
        ),
        PersonaCard(
            post_id=3,
            demographic_tags={"age_group": "18-24", "gender": "male", "income_bracket": "low_income"},
            text_excerpt="College student, can barely afford ramen.",
            sector="tech",
        ),
        PersonaCard(
            post_id=4,
            demographic_tags={"age_group": "45-54", "gender": "female", "income_bracket": "high_income"},
            text_excerpt="VP of engineering, we buy enterprise tools.",
            sector="tech",
        ),
    ]


@pytest.fixture
def product_description():
    return "A project management SaaS tool for small teams with AI-powered task prioritization."


@pytest.fixture
def price_points():
    return [49, 99, 199, 299, 499]


def _make_mock_client_for_van_westendorp(responses: list[dict]) -> MagicMock:
    """Build a mock client that returns Van Westendorp JSON responses in order."""
    client = MagicMock()
    side_effects = []
    for resp in responses:
        message = MagicMock()
        message.content = [MagicMock(text=json.dumps(resp))]
        side_effects.append(message)
    client.messages.create.side_effect = side_effects
    return client


def _make_mock_client_for_gabor_granger(responses: list[dict]) -> MagicMock:
    """Build a mock client that returns Gabor-Granger JSON responses in order."""
    client = MagicMock()
    side_effects = []
    for resp in responses:
        message = MagicMock()
        message.content = [MagicMock(text=json.dumps(resp))]
        side_effects.append(message)
    client.messages.create.side_effect = side_effects
    return client


# ── JSON Parsing ─────────────────────────────────────────────────────────────

class TestExtractJson:
    """Tests for robust JSON extraction from Claude responses."""

    def test_clean_json(self):
        from focus_groups.wtp.parsing import extract_json
        result = extract_json('{"too_cheap": 20, "cheap": 50}')
        assert result == {"too_cheap": 20, "cheap": 50}

    def test_json_with_markdown_fence(self):
        from focus_groups.wtp.parsing import extract_json
        text = 'Here is my answer:\n```json\n{"too_cheap": 20, "cheap": 50}\n```'
        result = extract_json(text)
        assert result == {"too_cheap": 20, "cheap": 50}

    def test_json_with_surrounding_text(self):
        from focus_groups.wtp.parsing import extract_json
        text = 'As a budget-conscious person, I would say:\n{"too_cheap": 10, "cheap": 30, "expensive": 80, "too_expensive": 150}\nHope that helps!'
        result = extract_json(text)
        assert result["too_cheap"] == 10
        assert result["too_expensive"] == 150

    def test_json_with_plain_fence(self):
        from focus_groups.wtp.parsing import extract_json
        text = '```\n{"49": true, "99": false}\n```'
        result = extract_json(text)
        assert result == {"49": True, "99": False}

    def test_invalid_json_raises(self):
        from focus_groups.wtp.parsing import extract_json
        import pytest
        with pytest.raises(ValueError, match="Could not extract JSON"):
            extract_json("I don't know the prices.")

    def test_empty_string_raises(self):
        from focus_groups.wtp.parsing import extract_json
        import pytest
        with pytest.raises(ValueError, match="Could not extract JSON"):
            extract_json("")

    def test_json_with_whitespace(self):
        from focus_groups.wtp.parsing import extract_json
        result = extract_json('  \n  {"a": 1}  \n  ')
        assert result == {"a": 1}


# ── Van Westendorp PSM ───────────────────────────────────────────────────────

class TestVanWestendorp:
    """Tests for Van Westendorp Price Sensitivity Meter."""

    def test_collect_psm_responses_calls_claude_per_persona(self, sample_cards, product_description):
        """Should make one Claude API call per persona."""
        from focus_groups.wtp.van_westendorp import collect_psm_responses

        responses = [
            {"too_cheap": 20, "cheap": 50, "expensive": 150, "too_expensive": 300},
            {"too_cheap": 30, "cheap": 60, "expensive": 120, "too_expensive": 250},
            {"too_cheap": 10, "cheap": 30, "expensive": 80, "too_expensive": 150},
            {"too_cheap": 40, "cheap": 80, "expensive": 200, "too_expensive": 400},
        ]
        client = _make_mock_client_for_van_westendorp(responses)

        results = collect_psm_responses(client, sample_cards, product_description)

        assert client.messages.create.call_count == 4
        assert len(results) == 4

    def test_collect_psm_responses_structure(self, sample_cards, product_description):
        """Each result should have post_id, demographics, and four price fields."""
        from focus_groups.wtp.van_westendorp import collect_psm_responses

        responses = [
            {"too_cheap": 20, "cheap": 50, "expensive": 150, "too_expensive": 300},
            {"too_cheap": 30, "cheap": 60, "expensive": 120, "too_expensive": 250},
            {"too_cheap": 10, "cheap": 30, "expensive": 80, "too_expensive": 150},
            {"too_cheap": 40, "cheap": 80, "expensive": 200, "too_expensive": 400},
        ]
        client = _make_mock_client_for_van_westendorp(responses)

        results = collect_psm_responses(client, sample_cards, product_description)

        for r in results:
            assert "post_id" in r
            assert "demographics" in r
            assert "too_cheap" in r
            assert "cheap" in r
            assert "expensive" in r
            assert "too_expensive" in r
            assert isinstance(r["too_cheap"], (int, float))

    def test_collect_psm_responses_empty_cards(self, product_description):
        """Empty card list should return empty results with no API calls."""
        from focus_groups.wtp.van_westendorp import collect_psm_responses

        client = MagicMock()
        results = collect_psm_responses(client, [], product_description)

        assert results == []
        client.messages.create.assert_not_called()

    def test_compute_psm_curves(self):
        """Should compute four cumulative distribution curves from raw responses."""
        from focus_groups.wtp.van_westendorp import compute_psm_curves

        raw = [
            {"post_id": 1, "demographics": {}, "too_cheap": 20, "cheap": 50, "expensive": 150, "too_expensive": 300},
            {"post_id": 2, "demographics": {}, "too_cheap": 30, "cheap": 60, "expensive": 120, "too_expensive": 250},
            {"post_id": 3, "demographics": {}, "too_cheap": 10, "cheap": 30, "expensive": 80, "too_expensive": 150},
            {"post_id": 4, "demographics": {}, "too_cheap": 40, "cheap": 80, "expensive": 200, "too_expensive": 400},
        ]

        curves = compute_psm_curves(raw)

        assert "price_points" in curves
        assert "too_cheap" in curves
        assert "cheap" in curves
        assert "expensive" in curves
        assert "too_expensive" in curves
        # All curve arrays should have the same length
        n = len(curves["price_points"])
        assert len(curves["too_cheap"]) == n
        assert len(curves["cheap"]) == n
        assert len(curves["expensive"]) == n
        assert len(curves["too_expensive"]) == n

    def test_find_price_points(self):
        """Should identify optimal price point and acceptable price range."""
        from focus_groups.wtp.van_westendorp import compute_psm_curves, find_price_points

        raw = [
            {"post_id": 1, "demographics": {}, "too_cheap": 20, "cheap": 50, "expensive": 150, "too_expensive": 300},
            {"post_id": 2, "demographics": {}, "too_cheap": 30, "cheap": 60, "expensive": 120, "too_expensive": 250},
            {"post_id": 3, "demographics": {}, "too_cheap": 10, "cheap": 30, "expensive": 80, "too_expensive": 150},
            {"post_id": 4, "demographics": {}, "too_cheap": 40, "cheap": 80, "expensive": 200, "too_expensive": 400},
        ]

        curves = compute_psm_curves(raw)
        price_pts = find_price_points(curves)

        assert "optimal_price" in price_pts
        assert "acceptable_range" in price_pts
        assert len(price_pts["acceptable_range"]) == 2
        low, high = price_pts["acceptable_range"]
        assert low <= price_pts["optimal_price"] <= high

    def test_psm_prompt_includes_product(self, sample_cards, product_description):
        """The prompt sent to Claude should contain the product description."""
        from focus_groups.wtp.van_westendorp import collect_psm_responses

        responses = [
            {"too_cheap": 20, "cheap": 50, "expensive": 150, "too_expensive": 300},
        ] * 4
        client = _make_mock_client_for_van_westendorp(responses)

        collect_psm_responses(client, sample_cards, product_description)

        first_call = client.messages.create.call_args_list[0]
        user_message = first_call[1]["messages"][0]["content"]
        assert "project management" in user_message.lower()

    def test_psm_prompt_requests_json(self, sample_cards, product_description):
        """The prompt should instruct Claude to return JSON."""
        from focus_groups.wtp.van_westendorp import collect_psm_responses

        responses = [
            {"too_cheap": 20, "cheap": 50, "expensive": 150, "too_expensive": 300},
        ] * 4
        client = _make_mock_client_for_van_westendorp(responses)

        collect_psm_responses(client, sample_cards, product_description)

        first_call = client.messages.create.call_args_list[0]
        user_message = first_call[1]["messages"][0]["content"]
        assert "json" in user_message.lower()


# ── Gabor-Granger ────────────────────────────────────────────────────────────

class TestGaborGranger:
    """Tests for Gabor-Granger demand simulation."""

    def test_collect_demand_responses_calls_claude_per_persona(
        self, sample_cards, product_description, price_points
    ):
        """Should make one Claude API call per persona."""
        from focus_groups.wtp.gabor_granger import collect_demand_responses

        responses = [
            {"49": True, "99": True, "199": True, "299": False, "499": False},
            {"49": True, "99": True, "199": False, "299": False, "499": False},
            {"49": True, "99": False, "199": False, "299": False, "499": False},
            {"49": True, "99": True, "199": True, "299": True, "499": False},
        ]
        client = _make_mock_client_for_gabor_granger(responses)

        results = collect_demand_responses(client, sample_cards, product_description, price_points)

        assert client.messages.create.call_count == 4
        assert len(results) == 4

    def test_collect_demand_responses_structure(
        self, sample_cards, product_description, price_points
    ):
        """Each result should have post_id, demographics, and purchase decisions per price."""
        from focus_groups.wtp.gabor_granger import collect_demand_responses

        responses = [
            {"49": True, "99": True, "199": True, "299": False, "499": False},
            {"49": True, "99": True, "199": False, "299": False, "499": False},
            {"49": True, "99": False, "199": False, "299": False, "499": False},
            {"49": True, "99": True, "199": True, "299": True, "499": False},
        ]
        client = _make_mock_client_for_gabor_granger(responses)

        results = collect_demand_responses(client, sample_cards, product_description, price_points)

        for r in results:
            assert "post_id" in r
            assert "demographics" in r
            assert "decisions" in r
            for p in price_points:
                assert str(p) in r["decisions"]
                assert isinstance(r["decisions"][str(p)], bool)

    def test_collect_demand_empty_cards(self, product_description, price_points):
        """Empty card list should return empty results with no API calls."""
        from focus_groups.wtp.gabor_granger import collect_demand_responses

        client = MagicMock()
        results = collect_demand_responses(client, [], product_description, price_points)

        assert results == []
        client.messages.create.assert_not_called()

    def test_compute_demand_curve(self, price_points):
        """Should compute % of cohort that would buy at each price."""
        from focus_groups.wtp.gabor_granger import compute_demand_curve

        raw = [
            {"post_id": 1, "demographics": {}, "decisions": {"49": True, "99": True, "199": True, "299": False, "499": False}},
            {"post_id": 2, "demographics": {}, "decisions": {"49": True, "99": True, "199": False, "299": False, "499": False}},
            {"post_id": 3, "demographics": {}, "decisions": {"49": True, "99": False, "199": False, "299": False, "499": False}},
            {"post_id": 4, "demographics": {}, "decisions": {"49": True, "99": True, "199": True, "299": True, "499": False}},
        ]

        curve = compute_demand_curve(raw, price_points)

        assert "price_points" in curve
        assert "demand_pct" in curve
        assert len(curve["price_points"]) == len(price_points)
        assert len(curve["demand_pct"]) == len(price_points)

        # At $49, all 4 would buy → 100%
        assert curve["demand_pct"][0] == 100.0
        # At $499, none would buy → 0%
        assert curve["demand_pct"][4] == 0.0
        # Demand should be non-increasing
        for i in range(len(curve["demand_pct"]) - 1):
            assert curve["demand_pct"][i] >= curve["demand_pct"][i + 1]

    def test_demand_prompt_includes_price_points(
        self, sample_cards, product_description, price_points
    ):
        """The prompt should include all price points."""
        from focus_groups.wtp.gabor_granger import collect_demand_responses

        responses = [
            {"49": True, "99": True, "199": True, "299": False, "499": False},
        ] * 4
        client = _make_mock_client_for_gabor_granger(responses)

        collect_demand_responses(client, sample_cards, product_description, price_points)

        first_call = client.messages.create.call_args_list[0]
        user_message = first_call[1]["messages"][0]["content"]
        assert "$49" in user_message
        assert "$499" in user_message


# ── Segmented Analysis ───────────────────────────────────────────────────────

class TestSegmentedAnalysis:
    """Tests for demographic segmentation of WTP results."""

    def test_segment_psm_by_dimension(self):
        """Should group PSM results by a demographic dimension."""
        from focus_groups.wtp.segmentation import segment_psm_by

        raw = [
            {"post_id": 1, "demographics": {"income_bracket": "high_income"}, "too_cheap": 40, "cheap": 80, "expensive": 200, "too_expensive": 400},
            {"post_id": 2, "demographics": {"income_bracket": "middle_income"}, "too_cheap": 20, "cheap": 50, "expensive": 120, "too_expensive": 250},
            {"post_id": 3, "demographics": {"income_bracket": "low_income"}, "too_cheap": 10, "cheap": 30, "expensive": 80, "too_expensive": 150},
            {"post_id": 4, "demographics": {"income_bracket": "high_income"}, "too_cheap": 50, "cheap": 90, "expensive": 250, "too_expensive": 500},
        ]

        segments = segment_psm_by(raw, "income_bracket")

        assert "high_income" in segments
        assert "middle_income" in segments
        assert "low_income" in segments
        assert len(segments["high_income"]) == 2
        assert len(segments["middle_income"]) == 1

    def test_segment_demand_by_dimension(self, price_points):
        """Should group demand results by a demographic dimension."""
        from focus_groups.wtp.segmentation import segment_demand_by

        raw = [
            {"post_id": 1, "demographics": {"income_bracket": "high_income"}, "decisions": {"49": True, "99": True, "199": True, "299": True, "499": False}},
            {"post_id": 2, "demographics": {"income_bracket": "low_income"}, "decisions": {"49": True, "99": False, "199": False, "299": False, "499": False}},
        ]

        segments = segment_demand_by(raw, "income_bracket")

        assert "high_income" in segments
        assert "low_income" in segments
        assert len(segments["high_income"]) == 1

    def test_segment_missing_dimension_grouped_as_unknown(self):
        """Personas missing the dimension should go in 'unknown' group."""
        from focus_groups.wtp.segmentation import segment_psm_by

        raw = [
            {"post_id": 1, "demographics": {"age_group": "25-34"}, "too_cheap": 20, "cheap": 50, "expensive": 150, "too_expensive": 300},
        ]

        segments = segment_psm_by(raw, "income_bracket")

        assert "unknown" in segments
        assert len(segments["unknown"]) == 1


# ── Visualization ────────────────────────────────────────────────────────────

class TestVisualization:
    """Tests for chart generation."""

    def test_plot_van_westendorp_returns_figure(self):
        """Should return a matplotlib Figure object."""
        from focus_groups.wtp.visualization import plot_van_westendorp

        curves = {
            "price_points": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            "too_cheap": [100, 90, 70, 50, 30, 15, 5, 2, 0, 0],
            "cheap": [100, 95, 85, 70, 50, 30, 15, 5, 2, 0],
            "expensive": [0, 2, 5, 15, 30, 50, 70, 85, 95, 100],
            "too_expensive": [0, 0, 2, 5, 15, 30, 50, 70, 90, 100],
        }
        price_pts = {"optimal_price": 55, "acceptable_range": [35, 75]}

        import matplotlib
        matplotlib.use("Agg")

        fig = plot_van_westendorp(curves, price_pts)

        import matplotlib.figure
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_plot_demand_curve_returns_figure(self):
        """Should return a matplotlib Figure object."""
        from focus_groups.wtp.visualization import plot_demand_curve

        curve = {
            "price_points": [49, 99, 199, 299, 499],
            "demand_pct": [100.0, 75.0, 50.0, 25.0, 0.0],
        }

        import matplotlib
        matplotlib.use("Agg")

        fig = plot_demand_curve(curve)

        import matplotlib.figure
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_plot_van_westendorp_saves_to_file(self, tmp_path):
        """Should be able to save the chart to a PNG file."""
        from focus_groups.wtp.visualization import plot_van_westendorp

        curves = {
            "price_points": [10, 20, 30, 40, 50],
            "too_cheap": [100, 70, 40, 10, 0],
            "cheap": [100, 80, 50, 20, 0],
            "expensive": [0, 20, 50, 80, 100],
            "too_expensive": [0, 10, 40, 70, 100],
        }
        price_pts = {"optimal_price": 30, "acceptable_range": [20, 40]}

        import matplotlib
        matplotlib.use("Agg")

        fig = plot_van_westendorp(curves, price_pts)
        out = tmp_path / "psm.png"
        fig.savefig(out)

        assert out.exists()
        assert out.stat().st_size > 0


# ── CLI Entry Point ──────────────────────────────────────────────────────────

class TestCLI:
    """Tests for CLI argument parsing and pipeline orchestration."""

    def test_parse_args_required_fields(self):
        """Should parse --product and --personas."""
        from focus_groups.wtp.cli import parse_args

        args = parse_args([
            "--product", "A SaaS tool",
            "--personas", "personas.json",
        ])

        assert args.product == "A SaaS tool"
        assert args.personas == "personas.json"

    def test_parse_args_optional_prices(self):
        """Should parse --prices as comma-separated list."""
        from focus_groups.wtp.cli import parse_args

        args = parse_args([
            "--product", "A SaaS tool",
            "--personas", "personas.json",
            "--prices", "49,99,199",
        ])

        assert args.prices == "49,99,199"

    def test_parse_args_output_dir(self):
        """Should parse --output-dir."""
        from focus_groups.wtp.cli import parse_args

        args = parse_args([
            "--product", "A tool",
            "--personas", "p.json",
            "--output-dir", "/tmp/wtp_out",
        ])

        assert args.output_dir == "/tmp/wtp_out"

    def test_load_personas_from_json(self, tmp_path):
        """Should load persona dicts from a JSON file and convert to PersonaCards."""
        from focus_groups.wtp.cli import load_personas

        data = [
            {
                "post_id": 1,
                "demographics": {"age_group": "25-34", "income_bracket": "high_income"},
                "subreddits": ["r/technology"],
                "sample_posts": ["I love SaaS tools"],
                "tags": {"sector": "tech"},
            },
            {
                "post_id": 2,
                "demographics": {"age_group": "35-44", "income_bracket": "low_income"},
                "subreddits": ["r/frugal"],
                "sample_posts": ["Always looking for deals"],
                "tags": {"sector": "tech"},
            },
        ]
        path = tmp_path / "personas.json"
        path.write_text(json.dumps(data))

        cards = load_personas(str(path))

        assert len(cards) == 2
        assert isinstance(cards[0], PersonaCard)
        assert cards[0].post_id == 1
        assert cards[0].demographic_tags["age_group"] == "25-34"

    def test_parse_prices_default(self):
        """Default prices should be used when --prices is not provided."""
        from focus_groups.wtp.cli import parse_prices

        result = parse_prices(None)
        assert isinstance(result, list)
        assert all(isinstance(p, int) for p in result)

    def test_parse_prices_custom(self):
        """Should parse comma-separated price string into int list."""
        from focus_groups.wtp.cli import parse_prices

        result = parse_prices("49,99,199,299")
        assert result == [49, 99, 199, 299]
