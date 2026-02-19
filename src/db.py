"""
Database connection and insert helpers.
Reads connection config from environment (falls back to localdev defaults).
"""

import os
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import execute_values, Json


def get_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DB", "focusgroups"),
        user=os.getenv("PG_USER", "fg_user"),
        password=os.getenv("PG_PASSWORD", "localdev"),
    )


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
