"""
Pricing model helpers for WTP analysis.

Supports three pricing models:
- one_time: single purchase price
- subscription: recurring monthly price
- hybrid: upfront fee + monthly subscription (normalized to 12-month total)
"""

from __future__ import annotations

from itertools import product as cartesian_product


def build_hybrid_price_points(
    upfront_points: list[float],
    sub_points: list[float],
) -> list[dict]:
    """Build all (upfront, monthly) combinations with 12-month totals.

    Returns a list of dicts sorted by total_12m:
        [{"upfront": 500, "monthly": 99, "total_12m": 1688}, ...]
    """
    tiers = []
    for upfront, monthly in cartesian_product(upfront_points, sub_points):
        tiers.append({
            "upfront": upfront,
            "monthly": monthly,
            "total_12m": upfront + monthly * 12,
        })
    tiers.sort(key=lambda t: t["total_12m"])
    return tiers


def normalize_for_display(
    pricing_model: str,
    price_points: list[float],
    upfront_points: list[float] | None = None,
    sub_points: list[float] | None = None,
) -> list[float]:
    """Return the effective price list for analysis.

    One-time and subscription: returns price_points as-is.
    Hybrid: returns sorted 12-month totals from all combinations.
    """
    if pricing_model == "hybrid":
        tiers = build_hybrid_price_points(upfront_points or [], sub_points or [])
        return [t["total_12m"] for t in tiers]
    return list(price_points)


def format_price_label(
    pricing_model: str,
    price: float,
    upfront: float | None = None,
    monthly: float | None = None,
) -> str:
    """Format a price for human-readable display.

    one_time:     "$99" or "$1,500"
    subscription: "$99/mo"
    hybrid:       "$500 setup + $99/mo ($1,688/yr total)"
    """
    if pricing_model == "subscription":
        return f"${price:,.0f}/mo"
    if pricing_model == "hybrid" and upfront is not None and monthly is not None:
        return f"${upfront:,.0f} setup + ${monthly:,.0f}/mo (${price:,.0f}/yr total)"
    return f"${price:,.0f}"
