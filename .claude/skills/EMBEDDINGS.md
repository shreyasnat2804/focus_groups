# EMBEDDINGS.md — Sentence Embeddings + pgvector

## Model Choice

**all-MiniLM-L6-v2** (384 dimensions)
- Fast, small (80MB), good quality for clustering/retrieval
- If quality isn't sufficient, upgrade to `all-mpnet-base-v2` (768 dims) — requires schema change

## Embedding Pipeline

```python
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_batch(texts: list[str], batch_size=256) -> np.ndarray:
    """Returns (N, 384) array of embeddings."""
    return model.encode(texts, batch_size=batch_size, show_progress_bar=True, normalize_embeddings=True)
```

## Writing to pgvector

```python
from pgvector.psycopg2 import register_vector
import psycopg2

conn = get_conn()
register_vector(conn)

def insert_embeddings(conn, post_ids: list[int], embeddings: np.ndarray, model_name: str):
    with conn.cursor() as cur:
        args = [(pid, model_name, emb.tolist()) for pid, emb in zip(post_ids, embeddings)]
        execute_values(
            cur,
            "INSERT INTO post_embeddings (post_id, model, embedding) VALUES %s ON CONFLICT (post_id) DO NOTHING",
            args,
        )
    conn.commit()
```

## Similarity Search

```python
def find_similar(conn, query_text: str, model, limit=20):
    query_emb = model.encode([query_text], normalize_embeddings=True)[0]
    with conn.cursor() as cur:
        cur.execute(
            "SELECT p.id, p.text, 1 - (pe.embedding <=> %s::vector) AS similarity "
            "FROM post_embeddings pe JOIN posts p ON pe.post_id = p.id "
            "ORDER BY pe.embedding <=> %s::vector LIMIT %s",
            (query_emb.tolist(), query_emb.tolist(), limit),
        )
        return cur.fetchall()
```

`<=>` is cosine distance in pgvector. `1 - distance = similarity`.

## HNSW Index

Build **after** all embeddings are inserted:

```sql
CREATE INDEX idx_embeddings_vector ON post_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);
```

- `m=16`: connections per node (default 16, higher = more accurate + more memory)
- `ef_construction=200`: build-time search width (higher = slower build, better recall)
- For 100k vectors this takes ~30 seconds. For 1M+, minutes.

## Batch Processing Workflow

```bash
# On Lambda GPU:
python3 src/embed.py \
    --batch-size 256 \
    --model all-MiniLM-L6-v2 \
    --start-id 0 \
    --chunk-size 10000
```

Process in chunks of 10k posts. Commit after each chunk. This way if the job crashes, you don't lose everything.

## Pitfalls

- **Normalize embeddings**: Always pass `normalize_embeddings=True`. Cosine similarity assumes unit vectors.
- **Dimension mismatch**: The `vector(384)` column type is fixed. If you change models, you need to ALTER or recreate the column.
- **Memory on GPU**: MiniLM is small (~80MB). Batch size of 256-512 is fine even on a small GPU. The bottleneck is DB writes, not encoding.
- **Don't build HNSW during inserts**: Build it once after bulk load. See DATABASE.md.
