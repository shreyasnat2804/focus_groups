"""
Maximal Marginal Relevance (MMR) — pure math, no DB dependency.
"""

from __future__ import annotations


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
