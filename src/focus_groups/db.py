"""
Database connection and insert helpers.
Reads connection config from environment (falls back to localdev defaults).
"""

import os
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import execute_values, Json
from pgvector.psycopg2 import register_vector


def get_conn():
    conn = psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DB", "focusgroups"),
        user=os.getenv("PG_USER", "fg_user"),
        password=os.getenv("PG_PASSWORD", "localdev"),
    )
    register_vector(conn)
    return conn


def _sanitize_text(s) -> str:
    """
    Ensure a string is valid UTF-8 before inserting into Postgres.
    Replaces any surrogate chars or lone high bytes with the Unicode
    replacement character (U+FFFD) so the DB never receives invalid bytes.
    """
    if not s:
        return s or ""
    # surrogatepass lets encode() handle lone surrogates as CESU-8 byte sequences;
    # the subsequent UTF-8 decode then replaces those invalid sequences with U+FFFD.
    return s.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")


def insert_posts(conn, posts: list[dict]) -> int:
    """
    Bulk-insert scraped posts. Skips duplicates (ON CONFLICT DO NOTHING).
    Returns number of rows actually inserted.
    """
    if not posts:
        return 0

    rows = []
    for p in posts:
        created = p.get("created_utc")
        if created and not isinstance(created, str):
            created = datetime.fromtimestamp(created, tz=timezone.utc)

        rows.append((
            p["id"],                         # source_id
            p.get("subreddit", ""),
            p.get("author", ""),
            _sanitize_text(p.get("title", "")),
            _sanitize_text(p.get("selftext", "")),  # text
            p.get("score", 0),
            p.get("num_comments", 0),
            created,
            p.get("scraped_at"),
            Json({                           # metadata JSONB
                "sector": p.get("sector"),
                "region": p.get("region"),   # None = US/global
                "permalink": p.get("permalink", ""),
            }),
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO posts
              (source_id, subreddit, author, title, text, score,
               num_comments, created_utc, scraped_at, metadata)
            VALUES %s
            ON CONFLICT (source_id) DO NOTHING
            """,
            rows,
        )
        inserted = cur.rowcount

    conn.commit()
    return inserted


# ---------------------------------------------------------------------------
# Embedding helpers (Stage 2)
# ---------------------------------------------------------------------------

def get_embedding_model_id(conn, model_name: str) -> int:
    """Return the id for a given model name from embedding_models table."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM embedding_models WHERE name = %s", (model_name,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Embedding model '{model_name}' not in embedding_models table.")
        return row[0]


def get_unembedded_posts(conn, limit: int = 1000, after_id: int = 0) -> list[dict]:
    """
    Return posts that have no entry in post_embeddings yet, ordered by id.
    Uses cursor-style pagination via after_id for resume support.
    Returns list of dicts with keys: id, text, title.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.id, p.title, p.text
            FROM posts p
            LEFT JOIN post_embeddings pe ON pe.post_id = p.id
            WHERE pe.post_id IS NULL
              AND p.id > %s
            ORDER BY p.id
            LIMIT %s
            """,
            (after_id, limit),
        )
        return [{"id": row[0], "title": row[1] or "", "text": row[2]} for row in cur.fetchall()]


def insert_embeddings(
    conn,
    post_ids: list[int],
    embeddings: list[list[float]],
    model_id: int,
) -> int:
    """
    Bulk-insert embeddings into post_embeddings. Skips duplicates.
    Returns number of rows actually inserted.
    """
    if not post_ids:
        return 0

    import numpy as np
    rows = [(pid, model_id, np.array(emb)) for pid, emb in zip(post_ids, embeddings)]

    with conn.cursor() as cur:
        # Use RETURNING to get accurate inserted count — execute_values rowcount
        # only reflects the last page (default page_size=100) not the total.
        inserted_ids = execute_values(
            cur,
            """
            INSERT INTO post_embeddings (post_id, model_id, embedding)
            VALUES %s
            ON CONFLICT (post_id) DO NOTHING
            RETURNING id
            """,
            rows,
            fetch=True,
        )
        inserted = len(inserted_ids)

    conn.commit()
    return inserted


def create_ivfflat_index(conn) -> None:
    """
    Build an ivfflat cosine index on post_embeddings.embedding.
    Run this AFTER all embeddings have been inserted — not during bulk load.
    lists=100 is appropriate for 10K–100K rows.
    """
    with conn.cursor() as cur:
        cur.execute("DROP INDEX IF EXISTS idx_embeddings_vector")
        cur.execute(
            """
            CREATE INDEX idx_embeddings_vector
            ON post_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            """
        )
    conn.commit()


def get_posts_with_embeddings(
    conn,
    demographic_filter: dict | None = None,
    sector: str | None = None,
    limit: int = 500,
) -> list[dict]:
    """
    Return posts that have embeddings, optionally filtered by demographic tags and sector.

    demographic_filter: {dimension_name: value} e.g. {"age_group": "25-34", "gender": "male"}
    sector: "tech" | "financial" | "political" | None

    Returns list of dicts: {post_id, embedding, title, text, sector, demographic_tags}
    """
    params: list = []
    where_clauses = ["pe.post_id IS NOT NULL"]

    # Sector filter via metadata JSONB
    if sector:
        where_clauses.append("p.metadata->>'sector' = %s")
        params.append(sector)

    # Demographic filter: post must have ALL specified tags
    if demographic_filter:
        for dimension, value in demographic_filter.items():
            where_clauses.append(
                """
                EXISTS (
                    SELECT 1 FROM demographic_tags dt2
                    JOIN demographic_values dv2 ON dv2.id = dt2.demographic_value_id
                    JOIN demographic_dimensions dd2 ON dd2.id = dv2.dimension_id
                    WHERE dt2.post_id = p.id
                      AND dd2.name = %s
                      AND dv2.value = %s
                )
                """
            )
            params.extend([dimension, value])

    where_sql = " AND ".join(where_clauses)

    query = f"""
        SELECT
            p.id,
            pe.embedding,
            p.title,
            p.text,
            p.metadata->>'sector' AS sector
        FROM posts p
        JOIN post_embeddings pe ON pe.post_id = p.id
        WHERE {where_sql}
        ORDER BY RANDOM()
        LIMIT %s
    """
    params.append(limit)

    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    # Fetch demographic tags for each returned post in one query
    if not rows:
        return []

    post_ids = [r[0] for r in rows]
    tags_by_post = _load_tags_for_posts(conn, post_ids)

    return [
        {
            "post_id": r[0],
            "embedding": list(r[1]),  # pgvector returns numpy array
            "title": r[2] or "",
            "text": r[3],
            "sector": r[4],
            "demographic_tags": tags_by_post.get(r[0], {}),
        }
        for r in rows
    ]


def _load_tags_for_posts(conn, post_ids: list[int]) -> dict[int, dict]:
    """Return {post_id: {dimension: value}} for the given post ids."""
    if not post_ids:
        return {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT dt.post_id, dd.name, dv.value
            FROM demographic_tags dt
            JOIN demographic_values dv ON dv.id = dt.demographic_value_id
            JOIN demographic_dimensions dd ON dd.id = dv.dimension_id
            WHERE dt.post_id = ANY(%s)
            """,
            (post_ids,),
        )
        result: dict[int, dict] = {}
        for post_id, dim, val in cur.fetchall():
            result.setdefault(post_id, {})[dim] = val
    return result


def get_post_ids_by_source_ids(conn, source_ids: list[str]) -> dict[str, int]:
    """
    Returns {source_id: db_id} for all matching posts.
    Missing source_ids are simply absent from the result dict.
    """
    if not source_ids:
        return {}

    with conn.cursor() as cur:
        cur.execute(
            "SELECT source_id, id FROM posts WHERE source_id = ANY(%s)",
            (source_ids,),
        )
        return {row[0]: row[1] for row in cur.fetchall()}


def load_demographic_value_ids(conn) -> dict[tuple[str, str], int]:
    """
    Returns {(dimension_name, value): demographic_value_id} from lookup tables.
    Small static set (~14 rows) — call once at startup and pass to insert_tags
    when doing bulk inserts to avoid repeated round-trips.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT dd.name, dv.value, dv.id
            FROM demographic_values dv
            JOIN demographic_dimensions dd ON dd.id = dv.dimension_id
            """
        )
        return {(row[0], row[1]): row[2] for row in cur.fetchall()}


def insert_tags(conn, tags: list[dict], value_ids: dict = None) -> int:
    """
    Bulk-insert demographic tags. ON CONFLICT DO NOTHING (idempotent re-runs).
    Each dict must have: post_id, dimension, value, confidence, method.
    value_ids: optional pre-loaded {(dimension, value): id} map — pass it when
               calling in a tight loop to avoid a DB round-trip per batch.
    Returns count of rows actually inserted.
    """
    if not tags:
        return 0

    if value_ids is None:
        value_ids = load_demographic_value_ids(conn)

    rows = [
        (
            t["post_id"],
            value_ids[(t["dimension"], t["value"])],
            t["confidence"],
            t["method"],
        )
        for t in tags
    ]

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO demographic_tags (post_id, demographic_value_id, confidence, method)
            VALUES %s
            ON CONFLICT (post_id, demographic_value_id, method) DO NOTHING
            """,
            rows,
        )
        inserted = cur.rowcount

    conn.commit()
    return inserted
