"""
Export posts + demographic tags to CSV for backup / downstream use.

Output: data/posts_tagged.csv
Columns:
    source_id, subreddit, sector, author, score, created_utc,
    text_preview, dimension, value, confidence, method

Posts with multiple tags produce one row per tag.
Posts with zero tags are omitted.

Usage:
    python3 scripts/export_csv.py             # summary line only
    python3 scripts/export_csv.py -v          # columns, row count, sample rows
"""

import argparse
import csv
from pathlib import Path

from focus_groups.db import get_conn

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "posts_tagged.csv"

TEXT_PREVIEW_CHARS = 200

# NOTE: do NOT use LEFT()/SUBSTRING() here — those functions count Unicode
# characters, which forces Postgres to parse every byte as UTF-8. Posts with
# invalid UTF-8 byte sequences (e.g. truncated multibyte chars from scraping)
# will raise CharacterNotInRepertoire. Fetching p.text raw is a passthrough
# with no byte-level validation; we truncate in Python instead.
QUERY = """
SELECT
    p.source_id,
    p.subreddit,
    p.metadata->>'sector'    AS sector,
    p.author,
    p.score,
    p.created_utc,
    p.text,
    dd.name                  AS dimension,
    dv.value,
    dt.confidence,
    dt.method
FROM posts p
JOIN demographic_tags       dt ON dt.post_id              = p.id
JOIN demographic_values     dv ON dv.id                   = dt.demographic_value_id
JOIN demographic_dimensions dd ON dd.id                   = dv.dimension_id
ORDER BY p.id, dd.name, dt.method
"""

COLUMNS = [
    "source_id", "subreddit", "sector", "author", "score",
    "created_utc", "text_preview", "dimension", "value", "confidence", "method",
]

SAMPLE_ROWS = 3


def _truncate(val, n: int) -> str:
    """Truncate a string to n chars in Python — safe for any byte content."""
    if val is None:
        return ""
    return str(val)[:n]


def main(verbose: bool = False) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(QUERY)
            raw_rows = cur.fetchall()

        # Truncate text_preview (column index 6) in Python, not SQL
        rows = [
            row[:6] + (_truncate(row[6], TEXT_PREVIEW_CHARS),) + row[7:]
            for row in raw_rows
        ]

        with open(OUTPUT_FILE, "w", newline="", encoding="utf-8", errors="replace") as f:
            writer = csv.writer(f)
            writer.writerow(COLUMNS)
            writer.writerows(rows)

        print(f"Exported {len(rows):,} rows → {OUTPUT_FILE}")

        if verbose:
            print(f"Columns ({len(COLUMNS)}): {', '.join(COLUMNS)}")
            if rows:
                print(f"\nFirst {min(SAMPLE_ROWS, len(rows))} rows:")
                for row in rows[:SAMPLE_ROWS]:
                    preview = str(row[6])[:60].replace("\n", " ")
                    print(
                        f"  {row[0]}  r/{row[1]}  [{row[7]}={row[8]}"
                        f"  conf={row[9]:.2f}  via={row[10]}]"
                        f"  \"{preview}...\""
                    )
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export tagged posts to CSV.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print column list and sample rows.")
    args = parser.parse_args()
    main(verbose=args.verbose)
