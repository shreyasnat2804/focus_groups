"""
Remove recurring megathread posts (same subreddit+title appearing 2+ times).
These are weekly stickies with no demographic signal.
Deletes from Postgres (CASCADE removes tags) and rewrites the JSONL.
"""

import json
from pathlib import Path

from focus_groups.db import get_conn

DATA_FILE = Path(__file__).parent.parent.parent / "data" / "posts.jsonl"


def main():
    conn = get_conn()
    cur = conn.cursor()

    # Find all source_ids belonging to recurring megathread titles
    cur.execute("""
        SELECT p.source_id, p.subreddit, p.title, cnt.n
        FROM posts p
        JOIN (
            SELECT subreddit, title, COUNT(*) AS n
            FROM posts
            GROUP BY subreddit, title
            HAVING COUNT(*) > 1
        ) cnt USING (subreddit, title)
        ORDER BY cnt.n DESC, p.subreddit, p.title
    """)
    rows = cur.fetchall()
    source_ids_to_delete = [r[0] for r in rows]

    print(f"Found {len(source_ids_to_delete)} megathread posts across {len(set((r[1],r[2]) for r in rows))} unique titles:")
    seen = set()
    for source_id, sub, title, n in rows:
        key = (sub, title)
        if key not in seen:
            print(f"  [{sub}] {title[:70]!r} — {n}x")
            seen.add(key)

    if not source_ids_to_delete:
        print("Nothing to delete.")
        conn.close()
        return

    # Delete from Postgres (CASCADE removes demographic_tags)
    cur.execute("DELETE FROM posts WHERE source_id = ANY(%s)", (source_ids_to_delete,))
    deleted_db = cur.rowcount
    conn.commit()
    print(f"\nDeleted {deleted_db} rows from Postgres (tags removed via CASCADE)")

    # Rewrite JSONL without deleted IDs
    delete_set = set(source_ids_to_delete)
    kept = 0
    removed = 0
    lines = []
    with open(DATA_FILE) as f:
        for line in f:
            try:
                post = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            if post["id"] in delete_set:
                removed += 1
            else:
                lines.append(line if line.endswith("\n") else line + "\n")
                kept += 1

    with open(DATA_FILE, "w") as f:
        f.writelines(lines)

    print(f"JSONL: kept {kept}, removed {removed}")
    print(f"\nFinal corpus: {kept} posts in JSONL, {deleted_db} removed.")
    conn.close()


if __name__ == "__main__":
    main()
