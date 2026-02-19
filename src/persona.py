"""
Persona selection engine.

Algorithm:
  1. Pull a candidate pool from Postgres (filtered by demographic tags + sector).
  2. Run Maximal Marginal Relevance (MMR) to pick N diverse posts.
  3. Return PersonaCard objects with tags + text excerpts.

Usage:
    from src.persona import select_personas
    cards = select_personas(conn, demographic_filter={"age_group": "25-34"}, sector="tech", n=50)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from src.db import get_posts_with_embeddings


@dataclass
class PersonaCard:
    post_id: int
    demographic_tags: dict  # {dimension: value}
    text_excerpt: str       # first 300 chars of post text
    sector: str | None

    def __repr__(self) -> str:
        tags = ", ".join(f"{k}={v}" for k, v in self.demographic_tags.items())
        excerpt = self.text_excerpt[:120].replace("\n", " ")
        return f"PersonaCard(id={self.post_id}, sector={self.sector}, [{tags}], \"{excerpt}...\")"


# ---------------------------------------------------------------------------
# MMR core (pure Python, no DB dependency)
# ---------------------------------------------------------------------------

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    # Vectors are expected to be unit-normalized; dot product == cosine similarity.
    return dot


def mmr_select(
    candidates: list,
    embeddings: list[list[float]],
    n: int,
    lambda_: float = 0.5,
) -> list:
    """
    Maximal Marginal Relevance selection.

    Picks n items from candidates that are mutually diverse (maximizing
    min cosine distance to already-selected items).

    Args:
        candidates:  list of any items (e.g. post dicts or ids)
        embeddings:  parallel list of unit-norm float vectors
        n:           how many to select
        lambda_:     0 = max diversity, 1 = max relevance (0.5 balanced)

    Returns:
        Subset of candidates (in selection order).
    """
    if not candidates:
        return []

    n = min(n, len(candidates))
    selected_indices: list[int] = []
    remaining = list(range(len(candidates)))

    # Seed with the first candidate (arbitrary but deterministic)
    first = remaining.pop(0)
    selected_indices.append(first)

    while len(selected_indices) < n and remaining:
        best_idx = None
        best_score = float("-inf")

        for idx in remaining:
            # Diversity: max cosine distance to already-selected items
            max_sim_to_selected = max(
                _cosine_similarity(embeddings[idx], embeddings[s])
                for s in selected_indices
            )
            # MMR score: balance relevance (1.0 since no query) vs. diversity
            mmr_score = lambda_ * 1.0 - (1 - lambda_) * max_sim_to_selected

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        remaining.remove(best_idx)
        selected_indices.append(best_idx)

    return [candidates[i] for i in selected_indices]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

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
