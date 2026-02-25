"""
Gabor-Granger demand simulation.

For a set of price points, asks each persona whether they would purchase
at each price. Aggregates into a demand curve showing % of cohort that
would buy at each price.
"""

from __future__ import annotations

import json

import anthropic

from focus_groups.personas.cards import PersonaCard
from focus_groups.personas.profiles import build_system_prompt, load_prompt_template
from focus_groups.claude import MODEL, MAX_TOKENS


def collect_demand_responses(
    client: anthropic.Anthropic,
    cards: list[PersonaCard],
    product_description: str,
    price_points: list[int],
) -> list[dict]:
    """
    Ask each persona whether they would buy at each price point via Claude.

    Returns:
        List of dicts with keys: post_id, demographics, decisions
        where decisions is {str(price): bool}.
    """
    if not cards:
        return []

    template = load_prompt_template("gabor_granger.txt")
    results = []

    price_points_str = ", ".join(f"${p}" for p in price_points)
    price_json_template = ", ".join(f'"{p}": true/false' for p in price_points)

    for card in cards:
        system_prompt = build_system_prompt(card)
        user_prompt = template.format(
            product_description=product_description,
            price_points_str=price_points_str,
            price_json_template=price_json_template,
        )

        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = message.content[0].text.strip()
        parsed = json.loads(raw_text)

        decisions = {}
        for p in price_points:
            key = str(p)
            decisions[key] = bool(parsed.get(key, False))

        results.append({
            "post_id": card.post_id,
            "demographics": dict(card.demographic_tags),
            "decisions": decisions,
        })

    return results


def compute_demand_curve(
    raw: list[dict],
    price_points: list[int],
) -> dict:
    """
    Aggregate individual purchase decisions into a demand curve.

    Returns:
        Dict with keys: price_points, demand_pct
        demand_pct is a list of floats (0-100) showing % who would buy at each price.
    """
    n = len(raw)
    if n == 0:
        return {"price_points": list(price_points), "demand_pct": [0.0] * len(price_points)}

    demand_pct = []
    for p in price_points:
        key = str(p)
        buyers = sum(1 for r in raw if r["decisions"].get(key, False))
        demand_pct.append(round(100.0 * buyers / n, 1))

    return {
        "price_points": list(price_points),
        "demand_pct": demand_pct,
    }
