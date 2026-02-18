"""Load existing data/posts.jsonl into Postgres. Safe to re-run (ON CONFLICT DO NOTHING)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from db import get_conn, insert_posts

JSONL = Path(__file__).parent.parent / "data" / "posts.jsonl"

conn = get_conn()
posts = []
with open(JSONL) as f:
    for line in f:
        line = line.strip()
        if line:
            posts.append(json.loads(line))

inserted = insert_posts(conn, posts)
conn.close()
print(f"Loaded {len(posts)} posts from JSONL → {inserted} inserted into DB")
