#!/usr/bin/env python3
"""
Stage 2: Batch embedding pipeline with resume support.

Processes all unembedded posts in chunks, writing embeddings back to Postgres.
Safe to re-run: skips posts already in post_embeddings.
After embedding, builds the ivfflat index.

Usage:
    python3 scripts/generate_embeddings.py [--chunk-size 1000] [--batch-size 256] [--index-only]

Env vars:
    EMBEDDING_PROVIDER = local | vertexai  (default: local)
    EMBEDDING_MODEL    = all-MiniLM-L6-v2  (default)
    EMBEDDING_DIM      = 384               (default)
    PG_HOST / PG_USER / PG_DB / PG_PASSWORD
"""

import argparse
import time

from focus_groups.db import (
    get_conn,
    get_embedding_model_id,
    get_unembedded_posts,
    insert_embeddings,
    create_ivfflat_index,
)
from focus_groups.embeddings import embed, EMBEDDING_MODEL


def count_unembedded(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM posts p
            LEFT JOIN post_embeddings pe ON pe.post_id = p.id
            WHERE pe.post_id IS NULL
            """
        )
        return cur.fetchone()[0]


def count_total_embedded(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM post_embeddings")
        return cur.fetchone()[0]


def build_text(post: dict) -> str:
    """Combine title + text for embedding. Title often has the key signal."""
    title = post.get("title", "") or ""
    text = post.get("text", "") or ""
    combined = f"{title}\n{text}".strip()
    return combined[:2000]  # cap at 2K chars to avoid tokenizer overflow


def run(chunk_size: int, batch_size: int, index_only: bool) -> None:
    conn = get_conn()
    model_id = get_embedding_model_id(conn, EMBEDDING_MODEL)

    if index_only:
        print("Building ivfflat index only...")
        create_ivfflat_index(conn)
        print("Index built.")
        return

    total_unembedded = count_unembedded(conn)
    already_done = count_total_embedded(conn)
    print(f"Posts to embed: {total_unembedded:,}  (already embedded: {already_done:,})")

    if total_unembedded == 0:
        print("All posts already embedded.")
    else:
        after_id = 0
        total_inserted = 0
        chunk_num = 0
        t0 = time.time()

        while True:
            posts = get_unembedded_posts(conn, limit=chunk_size, after_id=after_id)
            if not posts:
                break

            chunk_num += 1
            texts = [build_text(p) for p in posts]
            post_ids = [p["id"] for p in posts]

            print(
                f"  Chunk {chunk_num}: {len(posts)} posts "
                f"(ids {post_ids[0]}–{post_ids[-1]}) ... ",
                end="",
                flush=True,
            )

            vectors = embed(texts, batch_size=batch_size)
            inserted = insert_embeddings(conn, post_ids, vectors, model_id)
            total_inserted += inserted

            elapsed = time.time() - t0
            rate = total_inserted / elapsed if elapsed > 0 else 0
            print(f"inserted {inserted} ({rate:.0f} posts/sec)")

            after_id = post_ids[-1]

        print(f"\nDone. Embedded {total_inserted:,} posts in {time.time() - t0:.1f}s")

    # Build vector index
    total_embedded = count_total_embedded(conn)
    print(f"\nBuilding ivfflat index over {total_embedded:,} vectors...")
    t1 = time.time()
    create_ivfflat_index(conn)
    print(f"Index built in {time.time() - t1:.1f}s")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Batch embedding pipeline")
    parser.add_argument("--chunk-size", type=int, default=1000,
                        help="Posts per DB fetch/commit cycle (default: 1000)")
    parser.add_argument("--batch-size", type=int, default=256,
                        help="Texts per encoder batch (default: 256)")
    parser.add_argument("--index-only", action="store_true",
                        help="Skip embedding, just (re)build the ivfflat index")
    args = parser.parse_args()

    run(chunk_size=args.chunk_size, batch_size=args.batch_size, index_only=args.index_only)


if __name__ == "__main__":
    main()
