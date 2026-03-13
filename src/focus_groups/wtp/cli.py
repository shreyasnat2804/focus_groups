"""
CLI entry point for WTP (Willingness to Pay) analysis.

Usage:
    python wtp_analysis.py --product "description" --personas personas.json
    python wtp_analysis.py --product "description" --personas personas.json \
        --prices 49,99,199,299,499 --output-dir ./wtp_output --segment-by income_bracket
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from focus_groups.personas.cards import PersonaCard
from focus_groups.claude import get_client
from focus_groups.wtp.van_westendorp import (
    collect_psm_responses,
    compute_psm_curves,
    find_price_points,
)
from focus_groups.wtp.gabor_granger import (
    collect_demand_responses,
    compute_demand_curve,
)
from focus_groups.wtp.segmentation import segment_psm_by, segment_demand_by
from focus_groups.wtp.visualization import (
    plot_van_westendorp,
    plot_demand_curve,
    plot_segmented_demand,
)

DEFAULT_PRICES = [49, 99, 199, 299, 499]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Willingness to Pay analysis on persona cohort."
    )
    parser.add_argument(
        "--product", required=True, help="Product description string."
    )
    parser.add_argument(
        "--personas", required=True, help="Path to personas JSON file."
    )
    parser.add_argument(
        "--prices",
        default=None,
        help="Comma-separated price points for Gabor-Granger (default: 49,99,199,299,499).",
    )
    parser.add_argument(
        "--output-dir",
        default="./wtp_output",
        help="Directory to save charts and results (default: ./wtp_output).",
    )
    parser.add_argument(
        "--segment-by",
        default="income_bracket",
        help="Demographic dimension to segment by (default: income_bracket).",
    )
    return parser.parse_args(argv)


def parse_prices(prices_str: str | None) -> list[int]:
    """Parse comma-separated price string or return defaults."""
    if prices_str is None:
        return list(DEFAULT_PRICES)
    return [int(p.strip()) for p in prices_str.split(",")]


def load_personas(path: str) -> list[PersonaCard]:
    """
    Load persona dicts from a JSON file and convert to PersonaCards.

    Expected JSON format: list of objects with keys:
        post_id, demographics, subreddits, sample_posts, tags

    The text_excerpt is built from the first sample_post (or empty string).
    Sector is read from tags.sector (or None).
    """
    with open(path) as f:
        data = json.load(f)

    cards = []
    for item in data:
        sample_posts = item.get("sample_posts", [])
        text_excerpt = sample_posts[0] if sample_posts else ""
        sector = item.get("tags", {}).get("sector")

        cards.append(PersonaCard(
            post_id=item["post_id"],
            demographic_tags=item["demographics"],
            text_excerpt=text_excerpt[:300],
            sector=sector,
        ))

    return cards


def run_wtp_analysis(
    product: str,
    cards: list[PersonaCard],
    price_points: list[int],
    segment_by: str,
    output_dir: str,
    output=None,
) -> dict:
    """
    Run both Van Westendorp and Gabor-Granger analyses, produce charts.

    Returns:
        Dict with all results: psm_raw, psm_curves, psm_price_points,
        demand_raw, demand_curve, segments.
    """
    if output is None:
        output = sys.stdout

    import matplotlib
    matplotlib.use("Agg")

    os.makedirs(output_dir, exist_ok=True)
    client = get_client()

    # --- Van Westendorp PSM ---
    print(f"Running Van Westendorp PSM on {len(cards)} personas...", file=output)
    psm_raw = collect_psm_responses(client, cards, product)
    psm_curves = compute_psm_curves(psm_raw)
    psm_pts = find_price_points(psm_curves)

    print(f"  Optimal price: ${psm_pts['optimal_price']:.2f}", file=output)
    print(f"  Acceptable range: ${psm_pts['acceptable_range'][0]:.2f} - ${psm_pts['acceptable_range'][1]:.2f}", file=output)

    fig_psm = plot_van_westendorp(psm_curves, psm_pts)
    psm_path = os.path.join(output_dir, "van_westendorp.png")
    fig_psm.savefig(psm_path, dpi=150)
    print(f"  Chart saved: {psm_path}", file=output)

    # --- Gabor-Granger ---
    print(f"\nRunning Gabor-Granger demand simulation at {price_points}...", file=output)
    demand_raw = collect_demand_responses(client, cards, product, price_points)
    demand_curve = compute_demand_curve(demand_raw, price_points)

    for p, d in zip(demand_curve["price_points"], demand_curve["demand_pct"]):
        print(f"  ${p}: {d:.1f}% would buy", file=output)

    fig_demand = plot_demand_curve(demand_curve)
    demand_path = os.path.join(output_dir, "gabor_granger.png")
    fig_demand.savefig(demand_path, dpi=150)
    print(f"  Chart saved: {demand_path}", file=output)

    # --- Segmented Analysis ---
    print(f"\nSegmenting by {segment_by}...", file=output)

    psm_segments = segment_psm_by(psm_raw, segment_by)
    demand_segments = segment_demand_by(demand_raw, segment_by)

    segment_results = {}
    segment_demand_curves = {}

    for seg_name, seg_data in sorted(demand_segments.items()):
        seg_curve = compute_demand_curve(seg_data, price_points)
        segment_demand_curves[seg_name] = seg_curve
        print(f"  {seg_name} ({len(seg_data)} personas):", file=output)
        for p, d in zip(seg_curve["price_points"], seg_curve["demand_pct"]):
            print(f"    ${p}: {d:.1f}%", file=output)

    for seg_name, seg_data in sorted(psm_segments.items()):
        if len(seg_data) >= 2:
            seg_curves = compute_psm_curves(seg_data)
            seg_pts = find_price_points(seg_curves)
            segment_results[seg_name] = {
                "psm_optimal": seg_pts["optimal_price"],
                "psm_range": seg_pts["acceptable_range"],
                "n": len(seg_data),
            }
            print(f"  {seg_name} PSM optimal: ${seg_pts['optimal_price']:.2f} "
                  f"(range ${seg_pts['acceptable_range'][0]:.2f}-${seg_pts['acceptable_range'][1]:.2f})",
                  file=output)

    if segment_demand_curves:
        fig_seg = plot_segmented_demand(segment_demand_curves, f"Demand by {segment_by}")
        seg_path = os.path.join(output_dir, f"demand_by_{segment_by}.png")
        fig_seg.savefig(seg_path, dpi=150)
        print(f"  Segmented chart saved: {seg_path}", file=output)

    # --- Save raw JSON results ---
    results = {
        "product": product,
        "num_personas": len(cards),
        "van_westendorp": {
            "responses": psm_raw,
            "optimal_price": psm_pts["optimal_price"],
            "acceptable_range": psm_pts["acceptable_range"],
        },
        "gabor_granger": {
            "responses": demand_raw,
            "demand_curve": demand_curve,
        },
        "segments": {
            "dimension": segment_by,
            "psm": segment_results,
            "demand": {k: v for k, v in segment_demand_curves.items()},
        },
    }

    json_path = os.path.join(output_dir, "wtp_results.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved: {json_path}", file=output)

    return results


def main():
    args = parse_args()
    cards = load_personas(args.personas)
    price_points = parse_prices(args.prices)

    if not cards:
        print("No personas found in the input file.")
        sys.exit(1)

    print(f"Loaded {len(cards)} personas from {args.personas}")
    print(f"Product: {args.product}")
    print(f"Price points: {price_points}")
    print(f"Segment by: {args.segment_by}")
    print()

    run_wtp_analysis(
        product=args.product,
        cards=cards,
        price_points=price_points,
        segment_by=args.segment_by,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
