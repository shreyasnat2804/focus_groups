"""
Provider-agnostic embedding function.

Controlled by env vars:
  EMBEDDING_PROVIDER = "local" | "vertexai"
  EMBEDDING_MODEL    = "all-MiniLM-L6-v2"   (or "text-embedding-004" for Vertex AI)
  EMBEDDING_DIM      = 384                   (768 for Vertex AI)

Usage:
    from src.embeddings import embed
    vectors = embed(["text one", "text two"])   # list[list[float]]
"""

import os

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))

# Cache the model so it's only loaded once per process
_local_model = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        _local_model = SentenceTransformer(EMBEDDING_MODEL)
    return _local_model


def _embed_local(texts: list[str], batch_size: int = 256) -> list[list[float]]:
    model = _get_local_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


def _embed_vertexai(texts: list[str]) -> list[list[float]]:
    """Vertex AI text-embedding-004. Requires google-cloud-aiplatform installed."""
    from google.cloud import aiplatform
    from vertexai.language_models import TextEmbeddingModel

    model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
    embeddings = model.get_embeddings(texts)
    return [e.values for e in embeddings]


def embed(texts: list[str], batch_size: int = 256) -> list[list[float]]:
    """
    Embed a list of strings. Returns list of float vectors.
    Length of output == length of input.
    Vectors are L2-normalized (unit length).
    """
    if not texts:
        return []

    if EMBEDDING_PROVIDER == "vertexai":
        return _embed_vertexai(texts)
    else:
        return _embed_local(texts, batch_size=batch_size)
