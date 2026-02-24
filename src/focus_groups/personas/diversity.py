"""
Diversity metric for a set of embeddings.
"""

from __future__ import annotations

from focus_groups.personas.mmr import _cosine_similarity


def avg_pairwise_distance(embeddings: list[list[float]]) -> float:
    """
    Average cosine distance between all pairs of embeddings.

    distance = 1 - cosine_similarity  (range [0, 2] for unit vectors)
    Higher value means more diverse.

    Args:
        embeddings: list of unit-norm float vectors

    Returns:
        Average pairwise cosine distance, or 0.0 if fewer than 2 vectors.
    """
    if len(embeddings) < 2:
        return 0.0

    total, count = 0.0, 0
    for i in range(len(embeddings)):
        for j in range(i + 1, len(embeddings)):
            sim = _cosine_similarity(embeddings[i], embeddings[j])
            total += 1 - sim
            count += 1

    return total / count if count > 0 else 0.0
