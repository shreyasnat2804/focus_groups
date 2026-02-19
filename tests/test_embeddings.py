"""
Tests for src/embeddings.py

What we expect:
- embed() returns a list of lists of floats
- Output length matches input length
- Each vector has EMBEDDING_DIM dimensions
- Vectors are unit-normalized (L2 norm ≈ 1.0)
- Works with a single string and a batch
- EMBEDDING_PROVIDER env var switches between providers (local tested here)
"""

import os
import math
import pytest

# Force local provider for tests
os.environ.setdefault("EMBEDDING_PROVIDER", "local")
os.environ.setdefault("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
os.environ.setdefault("EMBEDDING_DIM", "384")

from src.embeddings import embed, EMBEDDING_DIM


def l2_norm(vec: list[float]) -> float:
    return math.sqrt(sum(x * x for x in vec))


def test_embed_single():
    result = embed(["Hello world"])
    assert len(result) == 1
    assert len(result[0]) == EMBEDDING_DIM


def test_embed_batch():
    texts = ["Finance is important", "Tech stocks fell", "Political debate"]
    result = embed(texts)
    assert len(result) == 3
    for vec in result:
        assert len(vec) == EMBEDDING_DIM


def test_embed_normalized():
    """All vectors should be unit-normalized (norm ≈ 1.0)."""
    texts = ["Test sentence one", "Another sentence here"]
    result = embed(texts)
    for vec in result:
        norm = l2_norm(vec)
        assert abs(norm - 1.0) < 1e-4, f"Expected unit norm, got {norm}"


def test_embed_returns_list_of_lists():
    result = embed(["Sample text"])
    assert isinstance(result, list)
    assert isinstance(result[0], list)
    assert isinstance(result[0][0], float)


def test_embed_empty_input():
    result = embed([])
    assert result == []


def test_embed_different_texts_differ():
    """Distinct texts should produce different vectors."""
    a = embed(["I love cats"])[0]
    b = embed(["The economy is struggling"])[0]
    assert a != b
