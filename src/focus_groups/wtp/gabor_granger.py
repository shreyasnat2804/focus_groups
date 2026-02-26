"""
Gabor-Granger demand simulation.

For a set of price points, asks each persona whether they would purchase
at each price. Aggregates into a demand curve showing % of cohort that
would buy at each price.
"""

from __future__ import annotations

from pathlib import Path

import anthropic

from focus_groups.personas.cards import PersonaCard
from focus_groups.personas.profiles import build_system_prompt, load_prompt_template
from focus_groups.claude import MODEL, MAX_TOKENS
from focus_groups.wtp.parsing import extract_json

WTP_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def _load_wtp_template(filename: str) -> str:
    """Load a prompt template from the wtp/prompts directory."""
    path = WTP_PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"WTP prompt template not found: {path}")
    return path.read_text().strip()


def collect_demand_responses(
    client: anthropic.Anthropic,
    cards: list[PersonaCard],
    product_description: str,
    price_points: list[int],
    pricing_model: str = "one_time",
    hybrid_tiers: list[dict] | None = None,
) -> list[dict]:
    """
    Ask each persona whether they would buy at each price point via Claude.

    Args:
        client: Anthropic API client.
        cards: List of PersonaCards to query.
        product_description: Description of the product being evaluated.
        price_points: List of price points to test (12m totals for hybrid).
        pricing_model: One of "one_time", "subscription", "hybrid".
        hybrid_tiers: For hybrid model, list of {upfront, monthly, total_12m} dicts.

    Returns:
        List of dicts with keys: post_id, demographics, decisions
        where decisions is {str(price): bool}.
    """
    if not cards:
        return []

    # Try model-specific template, fall back to generic
    try:
        template = _load_wtp_template(f"gabor_granger_{pricing_model}.txt")
    except FileNotFoundError:
        template = load_prompt_template("gabor_granger.txt")

    results = []

    # Format price points for prompt
    if pricing_model == "hybrid" and hybrid_tiers:
        price_points_str = "\n".join(
            f"  ${t['upfront']} setup + ${t['monthly']}/mo = ${t['total_12m']}/yr total"
            for t in hybrid_tiers
        )
        price_json_template = ", ".join(
            f'"{t["total_12m"]}": true/false' for t in hybrid_tiers
        )
    elif pricing_model == "subscription":
        price_points_str = ", ".join(f"${p}/mo" for p in price_points)
        price_json_template = ", ".join(f'"{p}": true/false' for p in price_points)
    else:
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
        parsed = extract_json(raw_text)

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
