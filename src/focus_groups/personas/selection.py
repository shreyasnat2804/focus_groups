"""
Public API for persona selection.
"""

from __future__ import annotations

from focus_groups.personas.cards import PersonaCard
from focus_groups.personas.mmr import mmr_select
from focus_groups.db import get_posts_with_embeddings


def select_personas(
    conn,
    demographic_filter: dict | None = None,
    sector: str | None = None,
    n: int = 50,
    pool_size: int = 500,
    excerpt_len: int = 300,
) -> list[PersonaCard]:
    """
    Select N diverse personas matching the given demographic/sector criteria.

    Steps:
      1. Pull up to pool_size candidate posts from Postgres (filtered).
      2. Run MMR over their embeddings to get n diverse posts.
      3. Wrap each in a PersonaCard.

    Args:
        conn:               psycopg2 connection (with pgvector registered)
        demographic_filter: e.g. {"age_group": "25-34", "gender": "female"}
        sector:             "tech" | "financial" | "political" | None
        n:                  number of personas to return
        pool_size:          candidate pool to draw from before MMR
        excerpt_len:        character length of text_excerpt in cards

    Returns:
        List of PersonaCard, length <= n.
    """
    posts = get_posts_with_embeddings(
        conn,
        demographic_filter=demographic_filter,
        sector=sector,
        limit=pool_size,
    )

    if not posts:
        return []

    embeddings = [p["embedding"] for p in posts]
    selected = mmr_select(posts, embeddings, n=n)

    cards = []
    for post in selected:
        text = post.get("text", "") or ""
        title = post.get("title", "") or ""
        combined = f"{title}\n{text}".strip()
        cards.append(
            PersonaCard(
                post_id=post["post_id"],
                demographic_tags=post.get("demographic_tags", {}),
                text_excerpt=combined[:excerpt_len],
                sector=post.get("sector"),
            )
        )

    return cards
