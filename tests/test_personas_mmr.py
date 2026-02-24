"""
Tests for personas/mmr.py

What we expect:
- mmr_select() returns exactly n items from a candidate pool
- Result is a subset of the input candidates
- No duplicate items in result
- When pool < n, return all candidates
- Empty input returns empty list
- _cosine_similarity of identical unit vectors = 1.0
- _cosine_similarity of orthogonal vectors = 0.0
"""

import math
import pytest
from personas.mmr import mmr_select, _cosine_similarity


def make_vecs(n: int, dim: int = 4) -> list[list[float]]:
    """Generate n random unit vectors for testing."""
    import random
    random.seed(42)
    vecs = []
    for _ in range(n):
        v = [random.gauss(0, 1) for _ in range(dim)]
        norm = math.sqrt(sum(x * x for x in v))
        vecs.append([x / norm for x in v])
    return vecs


# --- cosine similarity ---

def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert abs(_cosine_similarity(v, v) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert abs(_cosine_similarity(a, b)) < 1e-9


def test_cosine_similarity_opposite():
    v = [1.0, 0.0]
    neg = [-1.0, 0.0]
    assert abs(_cosine_similarity(v, neg) - (-1.0)) < 1e-9


# --- mmr_select ---

def test_mmr_returns_n_items():
    candidates = list(range(20))
    vecs = make_vecs(20)
    result = mmr_select(candidates, vecs, n=5)
    assert len(result) == 5


def test_mmr_subset_of_candidates():
    candidates = list(range(10))
    vecs = make_vecs(10)
    result = mmr_select(candidates, vecs, n=4)
    assert all(r in candidates for r in result)


def test_mmr_no_duplicates():
    candidates = list(range(10))
    vecs = make_vecs(10)
    result = mmr_select(candidates, vecs, n=6)
    assert len(result) == len(set(result))


def test_mmr_fewer_than_n():
    """When pool < n, return all candidates."""
    candidates = [1, 2, 3]
    vecs = make_vecs(3)
    result = mmr_select(candidates, vecs, n=10)
    assert len(result) == 3


def test_mmr_empty():
    result = mmr_select([], [], n=5)
    assert result == []


def test_mmr_single_candidate():
    result = mmr_select(["only"], [[1.0, 0.0]], n=3)
    assert result == ["only"]


def test_mmr_lambda_zero_maximizes_diversity():
    """lambda_=0 means pure diversity — second item should be most different from first."""
    # Two nearly identical and one orthogonal
    v1 = [1.0, 0.0]
    v2 = [0.9999, 0.01]   # very close to v1
    v3 = [0.0, 1.0]       # orthogonal to v1
    norm2 = math.sqrt(0.9999**2 + 0.01**2)
    v2 = [x / norm2 for x in v2]
    candidates = ["a", "b", "c"]
    vecs = [v1, v2, v3]
    result = mmr_select(candidates, vecs, n=2, lambda_=0)
    # First item is always "a" (seed); second should be "c" (most diverse)
    assert result[0] == "a"
    assert result[1] == "c"
