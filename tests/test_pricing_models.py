"""
Tests for pricing model normalization and label helpers.

Covers:
- Hybrid price point generation (cartesian product + 12-month totals)
- Normalization for one_time, subscription, and hybrid models
- Price label formatting for all three models
"""

from __future__ import annotations

import pytest


# ── build_hybrid_price_points ────────────────────────────────────────────────

class TestBuildHybridPricePoints:
    """Tests for cartesian product generation with 12-month totals."""

    def test_correct_cartesian_product(self):
        from focus_groups.wtp.pricing_models import build_hybrid_price_points

        result = build_hybrid_price_points([500, 1000], [49, 99])

        assert len(result) == 4  # 2 x 2

    def test_12m_totals(self):
        from focus_groups.wtp.pricing_models import build_hybrid_price_points

        result = build_hybrid_price_points([500], [99])

        assert len(result) == 1
        tier = result[0]
        assert tier["upfront"] == 500
        assert tier["monthly"] == 99
        assert tier["total_12m"] == 500 + 99 * 12  # 1688

    def test_multiple_combinations(self):
        from focus_groups.wtp.pricing_models import build_hybrid_price_points

        result = build_hybrid_price_points([500, 1000, 2500], [49, 99, 199])

        assert len(result) == 9  # 3 x 3
        # Verify all have correct keys
        for tier in result:
            assert "upfront" in tier
            assert "monthly" in tier
            assert "total_12m" in tier
            assert tier["total_12m"] == tier["upfront"] + tier["monthly"] * 12

    def test_sorted_by_total_12m(self):
        from focus_groups.wtp.pricing_models import build_hybrid_price_points

        result = build_hybrid_price_points([1000, 500], [199, 49])

        totals = [t["total_12m"] for t in result]
        assert totals == sorted(totals)


# ── normalize_for_display ────────────────────────────────────────────────────

class TestNormalizeForDisplay:
    """Tests for price normalization across pricing models."""

    def test_one_time_returns_unchanged(self):
        from focus_groups.wtp.pricing_models import normalize_for_display

        prices = [99, 199, 299]
        result = normalize_for_display("one_time", prices)

        assert result == prices

    def test_subscription_returns_unchanged(self):
        from focus_groups.wtp.pricing_models import normalize_for_display

        prices = [9, 19, 49]
        result = normalize_for_display("subscription", prices)

        assert result == prices

    def test_hybrid_returns_sorted_12m_totals(self):
        from focus_groups.wtp.pricing_models import normalize_for_display

        result = normalize_for_display(
            "hybrid",
            price_points=[],
            upfront_points=[500, 1000],
            sub_points=[49, 99],
        )

        expected = sorted([
            500 + 49 * 12,   # 1088
            500 + 99 * 12,   # 1688
            1000 + 49 * 12,  # 1588
            1000 + 99 * 12,  # 2188
        ])
        assert result == expected

    def test_hybrid_totals_ascending(self):
        from focus_groups.wtp.pricing_models import normalize_for_display

        result = normalize_for_display(
            "hybrid",
            price_points=[],
            upfront_points=[2500, 500, 1000],
            sub_points=[199, 49, 99],
        )

        assert result == sorted(result)


# ── format_price_label ───────────────────────────────────────────────────────

class TestFormatPriceLabel:
    """Tests for human-readable price label formatting."""

    def test_one_time(self):
        from focus_groups.wtp.pricing_models import format_price_label

        assert format_price_label("one_time", 99) == "$99"

    def test_one_time_large(self):
        from focus_groups.wtp.pricing_models import format_price_label

        assert format_price_label("one_time", 1500) == "$1,500"

    def test_subscription(self):
        from focus_groups.wtp.pricing_models import format_price_label

        assert format_price_label("subscription", 99) == "$99/mo"

    def test_hybrid(self):
        from focus_groups.wtp.pricing_models import format_price_label

        result = format_price_label("hybrid", 1688, upfront=500, monthly=99)

        assert "$500" in result
        assert "$99/mo" in result
        assert "$1,688/yr" in result

    def test_hybrid_format_full(self):
        from focus_groups.wtp.pricing_models import format_price_label

        result = format_price_label("hybrid", 2588, upfront=500, monthly=174)

        assert result == "$500 setup + $174/mo ($2,588/yr total)"
