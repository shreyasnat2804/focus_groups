"""Check for duplicate posts in Postgres and in the JSONL file."""

import json
from pathlib import Path
from collections import Counter

from focus_groups.db import get_conn

DATA_FILE = Path(__file__).parent.parent.parent / "data" / "posts.jsonl"


def check_db(conn):
    cur = conn.cursor()

    # Duplicate source_ids (should be 0 — UNIQUE constraint)
    cur.execute("""
        SELECT COUNT(*) AS total,
               COUNT(DISTINCT source_id) AS unique_source_ids
        FROM posts
    """)
    total, unique_ids = cur.fetchone()
    print("=== Postgres ===")
    print(f"  Total rows:          {total}")
    print(f"  Unique source_ids:   {unique_ids}")
    print(f"  Dup source_ids:      {total - unique_ids}")

    # Near-duplicate content: same subreddit + author + title
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT subreddit, author, title, COUNT(*) AS n
            FROM posts
            GROUP BY subreddit, author, title
            HAVING COUNT(*) > 1
        ) dups
    """)
    content_dups = cur.fetchone()[0]
    print(f"  Dup (sub+author+title) groups: {content_dups}")

    # Top duplicate groups if any
    if content_dups > 0:
        cur.execute("""
            SELECT subreddit, author, title, COUNT(*) AS n
            FROM posts
            GROUP BY subreddit, author, title
            HAVING COUNT(*) > 1
            ORDER BY n DESC
            LIMIT 5
        """)
        print("  Top duplicates:")
        for row in cur.fetchall():
            print(f"    [{row[0]}] {row[2][:60]!r} — {row[3]}x")


def check_jsonl():
    ids = []
    with open(DATA_FILE) as f:
        for line in f:
            try:
                ids.append(json.loads(line)["id"])
            except (json.JSONDecodeError, KeyError):
                pass

    counts = Counter(ids)
    dups = {k: v for k, v in counts.items() if v > 1}
    print("\n=== JSONL ===")
    print(f"  Total lines:    {len(ids)}")
    print(f"  Unique IDs:     {len(counts)}")
    print(f"  Duplicate IDs:  {len(dups)}")
    if dups:
        print("  Top duplicates:", sorted(dups.items(), key=lambda x: -x[1])[:5])


if __name__ == "__main__":
    conn = get_conn()
    check_db(conn)
    conn.close()
    check_jsonl()
