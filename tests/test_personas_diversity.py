"""
Tests for personas/diversity.py

What we expect:
- avg_pairwise_distance([v, v]) == 0.0  (identical vectors)
- avg_pairwise_distance([e1, e2]) == 1.0 for orthogonal unit vectors
- avg_pairwise_distance([]) == 0.0
- avg_pairwise_distance([v]) == 0.0  (single vector, no pairs)
- Result is in range [0, 2] (cosine distance bounds)
- Three-vector average is computed correctly
"""

import math
import pytest
from personas.diversity import avg_pairwise_distance


def test_identical_vectors_distance_zero():
    v = [1.0, 0.0, 0.0]
    result = avg_pairwise_distance([v, v])
    assert abs(result) < 1e-9


def test_orthogonal_vectors_distance_one():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    result = avg_pairwise_distance([a, b])
    assert abs(result - 1.0) < 1e-9


def test_opposite_vectors_distance_two():
    v = [1.0, 0.0]
    neg = [-1.0, 0.0]
    result = avg_pairwise_distance([v, neg])
    # cosine_sim = -1.0, distance = 1 - (-1) = 2
    assert abs(result - 2.0) < 1e-9


def test_empty_embeddings():
    assert avg_pairwise_distance([]) == 0.0


def test_single_embedding():
    assert avg_pairwise_distance([[1.0, 0.0]]) == 0.0


def test_three_vectors_average():
    """With 3 vectors, there are 3 pairs — verify the average."""
    e1 = [1.0, 0.0]
    e2 = [0.0, 1.0]
    e3 = [-1.0, 0.0]
    # Pair (e1,e2): sim=0, dist=1.0
    # Pair (e1,e3): sim=-1, dist=2.0
    # Pair (e2,e3): sim=0, dist=1.0
    expected = (1.0 + 2.0 + 1.0) / 3
    result = avg_pairwise_distance([e1, e2, e3])
    assert abs(result - expected) < 1e-9


def test_result_non_negative():
    import random
    random.seed(0)
    vecs = []
    for _ in range(5):
        v = [random.gauss(0, 1) for _ in range(8)]
        norm = math.sqrt(sum(x * x for x in v))
        vecs.append([x / norm for x in v])
    result = avg_pairwise_distance(vecs)
    assert result >= 0.0
