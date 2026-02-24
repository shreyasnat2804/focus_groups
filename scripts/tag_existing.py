"""
Retroactively tag posts already in the DB that have no demographic_tags rows.
Processes in batches of 500.

Usage:
    python3 scripts/tag_existing.py           # summary only
    python3 scripts/tag_existing.py -v        # per-batch progress
"""

import argparse

from focus_groups.db import get_conn, insert_tags
from focus_groups.tagger import tag_post

BATCH_SIZE = 500


def fetch_batch_after(conn, after_id: int, limit: int) -> list[dict]:
    """Return up to `limit` posts with id > after_id, ordered by id.
    Scans all posts regardless of tag status — safe for cursor pagination.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.id, p.subreddit, p.title, p.text,
                   EXISTS(SELECT 1 FROM demographic_tags dt WHERE dt.post_id = p.id) AS already_tagged
            FROM posts p
            WHERE p.id > %s
            ORDER BY p.id
            LIMIT %s
            """,
            (after_id, limit),
        )
        rows = cur.fetchall()
    return [
        {"id": row[0], "subreddit": row[1], "title": row[2], "text": row[3], "already_tagged": row[4]}
        for row in rows
    ]


def main(verbose: bool = False) -> None:
    conn = get_conn()
    try:
        last_id = 0
        total_posts = 0
        total_skipped = 0
        total_tagged = 0
        batch_num = 0

        while True:
            batch = fetch_batch_after(conn, last_id, BATCH_SIZE)
            if not batch:
                break

            batch_num += 1
            tag_rows = []
            for post in batch:
                if post["already_tagged"]:
                    total_skipped += 1
                    continue
                text = f"{post['title'] or ''} {post['text'] or ''}"
                for tag in tag_post(text, post["subreddit"] or ""):
                    tag["post_id"] = post["id"]
                    tag_rows.append(tag)

            if tag_rows:
                n = insert_tags(conn, tag_rows)
                total_tagged += n
            else:
                n = 0

            total_posts += len(batch)
            last_id = batch[-1]["id"]

            if verbose:
                newly = len(batch) - total_skipped % BATCH_SIZE
                print(
                    f"Batch {batch_num}: {len(batch)} posts "
                    f"({total_skipped % BATCH_SIZE} already tagged), "
                    f"inserted {n} tags (total: {total_tagged})"
                )

        print(
            f"Done. {total_posts:,} posts scanned, "
            f"{total_skipped:,} already tagged, "
            f"{total_tagged:,} new tag rows inserted."
        )
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tag untagged posts in DB.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print per-batch progress.")
    args = parser.parse_args()
    main(verbose=args.verbose)
