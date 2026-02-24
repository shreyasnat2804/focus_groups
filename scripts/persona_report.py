#!/usr/bin/env python3
"""
Stage 2: Persona spot-check report.

Prints N sample persona cards matching given demographic/sector criteria.
Useful for manual review to verify persona authenticity and diversity.

Usage:
    python3 scripts/persona_report.py --n 5
    python3 scripts/persona_report.py --sector tech --age-group 25-34 --gender male --n 10
    python3 scripts/persona_report.py --sector financial --n 5

Env vars: PG_HOST / PG_USER / PG_DB / PG_PASSWORD
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import get_conn
from personas import select_personas, avg_pairwise_distance


def _fetch_embeddings_for_cards(cards) -> list[list[float]]:
    """Re-fetch embeddings from DB for the given PersonaCards."""
    if not cards:
        return []
    conn = get_conn()
    post_ids = [c.post_id for c in cards]
    with conn.cursor() as cur:
        cur.execute(
            "SELECT post_id, embedding FROM post_embeddings WHERE post_id = ANY(%s)",
            (post_ids,),
        )
        emb_map = {row[0]: list(row[1]) for row in cur.fetchall()}
    conn.close()
    return [emb_map[c.post_id] for c in cards if c.post_id in emb_map]


def main():
    parser = argparse.ArgumentParser(description="Persona spot-check report")
    parser.add_argument("--n", type=int, default=5, help="Number of personas (default: 5)")
    parser.add_argument("--sector", choices=["tech", "financial", "political"],
                        help="Filter by sector")
    parser.add_argument("--age-group", dest="age_group",
                        help='Filter by age group, e.g. "25-34"')
    parser.add_argument("--gender", help='Filter by gender, e.g. "male"')
    parser.add_argument("--income", help='Filter by income bracket, e.g. "middle_income"')
    parser.add_argument("--pool-size", type=int, default=500,
                        help="Candidate pool size before MMR (default: 500)")
    args = parser.parse_args()

    demo_filter: dict = {}
    if args.age_group:
        demo_filter["age_group"] = args.age_group
    if args.gender:
        demo_filter["gender"] = args.gender
    if args.income:
        demo_filter["income_bracket"] = args.income

    conn = get_conn()

    # Check we have embeddings
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM post_embeddings")
        count = cur.fetchone()[0]

    if count == 0:
        print("No embeddings found. Run scripts/generate_embeddings.py first.")
        conn.close()
        return

    print(f"\n{'='*60}")
    print(f"  Persona Report")
    print(f"  n={args.n}, sector={args.sector or 'any'}, filters={demo_filter or 'none'}")
    print(f"{'='*60}\n")

    cards = select_personas(
        conn,
        demographic_filter=demo_filter or None,
        sector=args.sector,
        n=args.n,
        pool_size=args.pool_size,
    )

    if not cards:
        print("No personas found matching criteria.")
        print("Try removing filters or running generate_embeddings.py first.")
        conn.close()
        return

    for i, card in enumerate(cards, 1):
        tags = " | ".join(f"{k}: {v}" for k, v in sorted(card.demographic_tags.items()))
        print(f"--- Persona {i} (post_id={card.post_id}, sector={card.sector}) ---")
        if tags:
            print(f"    Demographics: {tags}")
        else:
            print(f"    Demographics: (none tagged)")
        print(f"    Excerpt: {card.text_excerpt[:300]!r}")
        print()

    avg_dist = avg_pairwise_distance(_fetch_embeddings_for_cards(cards))
    print(f"{'='*60}")
    print(f"  Avg pairwise cosine distance: {avg_dist:.4f}  (target > 0.3)")
    print(f"  Total personas returned: {len(cards)}")
    if avg_dist >= 0.3:
        print("  [PASS] Diversity looks good.")
    else:
        print("  [WARN] Low diversity — consider increasing pool_size or loosening filters.")
    print(f"{'='*60}\n")

    conn.close()


if __name__ == "__main__":
    main()
