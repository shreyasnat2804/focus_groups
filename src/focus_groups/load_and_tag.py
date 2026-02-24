"""
Loads any JSONL posts not yet in Postgres, then tags all untagged posts.
Safe to re-run — uses ON CONFLICT DO NOTHING throughout.
"""

import json
from pathlib import Path

from focus_groups.db import (
    get_conn,
    insert_posts,
    load_demographic_value_ids,
    insert_tags,
    get_post_ids_by_source_ids,
)
from focus_groups.tagger import tag_post

DATA_FILE = Path(__file__).parent.parent.parent / "data" / "posts.jsonl"
BATCH_SIZE = 500


def main():
    conn = get_conn()
    value_ids = load_demographic_value_ids(conn)

    posts = []
    with open(DATA_FILE) as f:
        for line in f:
            try:
                posts.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                pass

    print(f"Loaded {len(posts)} posts from JSONL")

    total_inserted = 0
    total_tagged = 0

    for i in range(0, len(posts), BATCH_SIZE):
        batch = posts[i : i + BATCH_SIZE]

        n = insert_posts(conn, batch)
        total_inserted += n

        id_map = get_post_ids_by_source_ids(conn, [p["id"] for p in batch])
        tag_rows = []
        for post in batch:
            db_id = id_map.get(post["id"])
            if db_id is None:
                continue
            text = f"{post.get('title', '')} {post.get('selftext', '')}"
            for tag in tag_post(text, post["subreddit"]):
                tag["post_id"] = db_id
                tag_rows.append(tag)

        if tag_rows:
            n_tags = insert_tags(conn, tag_rows, value_ids=value_ids)
            total_tagged += n_tags

        done = i + len(batch)
        if done % 2500 == 0 or done == len(posts):
            print(f"  {done}/{len(posts)} processed — {total_inserted} inserted, {total_tagged} tags written")

    conn.close()
    print(f"\nDone. {total_inserted} new posts inserted, {total_tagged} new tags inserted.")


if __name__ == "__main__":
    main()
