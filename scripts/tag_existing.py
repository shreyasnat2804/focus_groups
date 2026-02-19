"""
Retroactively tag posts already in the DB that have no demographic_tags rows.
Processes in batches of 500.

Usage:
    python3 scripts/tag_existing.py           # summary only
    python3 scripts/tag_existing.py -v        # per-batch progress
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_conn, insert_tags
from src.tagger import tag_post

BATCH_SIZE = 500


def fetch_untagged_batch(conn, offset: int, limit: int) -> list[dict]:
    """Return up to `limit` posts that have no demographic_tags rows."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.id, p.subreddit, p.title, p.text
            FROM posts p
            WHERE NOT EXISTS (
                SELECT 1 FROM demographic_tags dt WHERE dt.post_id = p.id
            )
            ORDER BY p.id
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        rows = cur.fetchall()
    return [
        {"id": row[0], "subreddit": row[1], "title": row[2], "text": row[3]}
        for row in rows
    ]


def main(verbose: bool = False) -> None:
    conn = get_conn()
    try:
        offset = 0
        total_tagged = 0
        batch_num = 0

        while True:
            batch = fetch_untagged_batch(conn, offset, BATCH_SIZE)
            if not batch:
                break

            batch_num += 1
            tag_rows = []
            for post in batch:
                text = f"{post['title'] or ''} {post['text'] or ''}"
                for tag in tag_post(text, post["subreddit"] or ""):
                    tag["post_id"] = post["id"]
                    tag_rows.append(tag)

            if tag_rows:
                n = insert_tags(conn, tag_rows)
                total_tagged += n
            else:
                n = 0

            if verbose:
                print(
                    f"Batch {batch_num}: processed {len(batch)} posts, "
                    f"inserted {n} tags (total tags: {total_tagged})"
                )
            offset += len(batch)

        print(f"Done. {offset:,} posts processed, {total_tagged:,} tag rows inserted.")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tag untagged posts in DB.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print per-batch progress.")
    args = parser.parse_args()
    main(verbose=args.verbose)
