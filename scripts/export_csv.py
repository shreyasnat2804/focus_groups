"""
Export posts + demographic tags to CSV for backup / downstream use.

Output: data/posts_tagged.csv
Columns:
    source_id, subreddit, sector, author, score, created_utc,
    text_preview, dimension, value, confidence, method

Posts with multiple tags produce one row per tag.
Posts with zero tags are omitted (use a LEFT JOIN variant if you need them).

Usage:
    python3 scripts/export_csv.py
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_conn

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "posts_tagged.csv"

TEXT_PREVIEW_CHARS = 200

QUERY = """
SELECT
    p.source_id,
    p.subreddit,
    p.metadata->>'sector'   AS sector,
    p.author,
    p.score,
    p.created_utc,
    LEFT(p.text, %(preview)s)  AS text_preview,
    dt.dimension,
    dt.value,
    dt.confidence,
    dt.method
FROM posts p
JOIN demographic_tags dt ON dt.post_id = p.id
ORDER BY p.id, dt.dimension, dt.method
"""

COLUMNS = [
    "source_id", "subreddit", "sector", "author", "score",
    "created_utc", "text_preview", "dimension", "value", "confidence", "method",
]


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(QUERY, {"preview": TEXT_PREVIEW_CHARS})
            rows = cur.fetchall()

        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(COLUMNS)
            writer.writerows(rows)

        print(f"Exported {len(rows):,} rows → {OUTPUT_FILE}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
