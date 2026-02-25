"""
Van Westendorp Price Sensitivity Meter (PSM).

Prompts each persona for four price thresholds, then aggregates into
cumulative distribution curves to find the optimal price point and
acceptable price range.
"""

from __future__ import annotations

import numpy as np
import anthropic

from focus_groups.personas.cards import PersonaCard
from focus_groups.personas.profiles import build_system_prompt, load_prompt_template
from focus_groups.claude import MODEL, MAX_TOKENS
from focus_groups.wtp.parsing import extract_json

PSM_KEYS = ("too_cheap", "cheap", "expensive", "too_expensive")


def collect_psm_responses(
    client: anthropic.Anthropic,
    cards: list[PersonaCard],
    product_description: str,
) -> list[dict]:
    """
    Ask each persona the four Van Westendorp questions via Claude.

    Returns:
        List of dicts with keys: post_id, demographics, too_cheap, cheap,
        expensive, too_expensive (all dollar amounts).
    """
    if not cards:
        return []

    template = load_prompt_template("van_westendorp.txt")
    results = []

    for card in cards:
        system_prompt = build_system_prompt(card)
        user_prompt = template.format(product_description=product_description)

        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = message.content[0].text.strip()
        parsed = extract_json(raw_text)

        results.append({
            "post_id": card.post_id,
            "demographics": dict(card.demographic_tags),
            "too_cheap": float(parsed["too_cheap"]),
            "cheap": float(parsed["cheap"]),
            "expensive": float(parsed["expensive"]),
            "too_expensive": float(parsed["too_expensive"]),
        })

    return results


def compute_psm_curves(
    raw: list[dict],
    num_points: int = 100,
) -> dict:
    """
    Compute four cumulative distribution curves from raw PSM responses.

    For each price on a uniform grid:
    - too_cheap:    % of respondents who said this price is "too cheap" or higher
                    (i.e. cumulative from high to low — starts at 100%, drops to 0%)
    - cheap:        % who said "bargain" at or above this price (same direction)
    - expensive:    % who said "expensive" at or below this price
                    (cumulative from low to high — starts at 0%, rises to 100%)
    - too_expensive: % who said "too expensive" at or below this price (same direction)

    Returns:
        Dict with keys: price_points, too_cheap, cheap, expensive, too_expensive
        Each value is a list of floats (percentages 0-100).
    """
    n = len(raw)
    if n == 0:
        return {"price_points": [], "too_cheap": [], "cheap": [], "expensive": [], "too_expensive": []}

    all_values = []
    for r in raw:
        for k in PSM_KEYS:
            all_values.append(r[k])

    lo = min(all_values)
    hi = max(all_values)
    price_points = np.linspace(lo, hi, num_points).tolist()

    tc_values = [r["too_cheap"] for r in raw]
    c_values = [r["cheap"] for r in raw]
    e_values = [r["expensive"] for r in raw]
    te_values = [r["too_expensive"] for r in raw]

    # too_cheap curve: % who think this price is too cheap (price <= their threshold)
    # At low prices, most people think it's too cheap → high %; drops as price rises
    too_cheap_curve = [
        100.0 * sum(1 for v in tc_values if p <= v) / n
        for p in price_points
    ]

    # cheap/bargain curve: % who think this price is a bargain (price <= their threshold)
    cheap_curve = [
        100.0 * sum(1 for v in c_values if p <= v) / n
        for p in price_points
    ]

    # expensive curve: % who think this price is expensive (price >= their threshold)
    expensive_curve = [
        100.0 * sum(1 for v in e_values if p >= v) / n
        for p in price_points
    ]

    # too_expensive curve: % who think this price is too expensive (price >= their threshold)
    too_expensive_curve = [
        100.0 * sum(1 for v in te_values if p >= v) / n
        for p in price_points
    ]

    return {
        "price_points": price_points,
        "too_cheap": too_cheap_curve,
        "cheap": cheap_curve,
        "expensive": expensive_curve,
        "too_expensive": too_expensive_curve,
    }


def find_price_points(curves: dict) -> dict:
    """
    Find the optimal price point (OPP) and acceptable price range from PSM curves.

    OPP: where "too cheap" and "too expensive" curves cross.
    Acceptable range: from where "too cheap" crosses "expensive" (PMC)
                      to where "cheap" crosses "too expensive" (PME).

    Returns:
        Dict with keys: optimal_price, acceptable_range (list of [low, high]).
    """
    prices = curves["price_points"]
    tc = curves["too_cheap"]
    c = curves["cheap"]
    e = curves["expensive"]
    te = curves["too_expensive"]

    def _find_crossing(curve_a, curve_b):
        """Find the price where curve_a crosses below curve_b."""
        for i in range(1, len(prices)):
            diff_prev = curve_a[i - 1] - curve_b[i - 1]
            diff_curr = curve_a[i] - curve_b[i]
            if diff_prev >= 0 and diff_curr <= 0:
                # Linear interpolation
                if diff_prev == diff_curr:
                    return prices[i]
                frac = diff_prev / (diff_prev - diff_curr)
                return prices[i - 1] + frac * (prices[i] - prices[i - 1])
        return prices[-1]

    # OPP: too_cheap crosses too_expensive
    optimal = _find_crossing(tc, te)

    # PMC (Point of Marginal Cheapness): too_cheap crosses expensive
    pmc = _find_crossing(tc, e)

    # PME (Point of Marginal Expensiveness): cheap crosses too_expensive
    pme = _find_crossing(c, te)

    return {
        "optimal_price": round(optimal, 2),
        "acceptable_range": [round(pmc, 2), round(pme, 2)],
    }
