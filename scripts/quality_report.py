"""
Data quality report — coverage analysis for demographic tags.

Prints:
  - Total posts in DB
  - Posts with ≥1 tag (and %)
  - Per-dimension coverage
  - Breakdown by sector
  - Top 5 values per dimension

Usage:
    python3 scripts/quality_report.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_conn


def run_report(conn) -> None:
    with conn.cursor() as cur:

        # Total posts
        cur.execute("SELECT COUNT(*) FROM posts")
        total_posts = cur.fetchone()[0]

        # Posts with ≥1 tag
        cur.execute(
            "SELECT COUNT(DISTINCT post_id) FROM demographic_tags"
        )
        tagged_posts = cur.fetchone()[0]

        pct_tagged = (tagged_posts / total_posts * 100) if total_posts else 0.0

        print("=" * 60)
        print("DEMOGRAPHIC TAGGING QUALITY REPORT")
        print("=" * 60)
        print(f"Total posts in DB       : {total_posts:,}")
        print(f"Posts with ≥1 tag       : {tagged_posts:,}  ({pct_tagged:.1f}%)")
        print()

        # Per-dimension coverage
        dimensions = ["age_group", "gender", "parent_status", "income_bracket"]
        print("DIMENSION COVERAGE")
        print("-" * 40)
        for dim in dimensions:
            cur.execute(
                "SELECT COUNT(DISTINCT post_id) FROM demographic_tags WHERE dimension = %s",
                (dim,),
            )
            count = cur.fetchone()[0]
            pct = (count / total_posts * 100) if total_posts else 0.0
            print(f"  {dim:<20} {count:>7,}  ({pct:.1f}%)")
        print()

        # Breakdown by sector
        print("TAGGED POSTS BY SECTOR")
        print("-" * 40)
        cur.execute(
            """
            SELECT
                p.metadata->>'sector' AS sector,
                COUNT(DISTINCT p.id) AS total,
                COUNT(DISTINCT dt.post_id) AS tagged
            FROM posts p
            LEFT JOIN demographic_tags dt ON dt.post_id = p.id
            GROUP BY sector
            ORDER BY total DESC
            """
        )
        rows = cur.fetchall()
        for sector, total, tagged in rows:
            pct = (tagged / total * 100) if total else 0.0
            sector_label = sector or "(none)"
            print(f"  {sector_label:<20} {total:>7,} posts,  {tagged:>7,} tagged  ({pct:.1f}%)")
        print()

        # Top 5 values per dimension
        print("TOP VALUES PER DIMENSION")
        print("-" * 40)
        for dim in dimensions:
            cur.execute(
                """
                SELECT value, COUNT(*) AS cnt
                FROM demographic_tags
                WHERE dimension = %s
                GROUP BY value
                ORDER BY cnt DESC
                LIMIT 5
                """,
                (dim,),
            )
            rows = cur.fetchall()
            print(f"  {dim}:")
            if rows:
                for value, cnt in rows:
                    print(f"    {value:<20} {cnt:>7,}")
            else:
                print("    (no data)")
            print()

        # Method breakdown
        print("TAG METHOD BREAKDOWN")
        print("-" * 40)
        cur.execute(
            """
            SELECT method, COUNT(*) AS cnt
            FROM demographic_tags
            GROUP BY method
            ORDER BY cnt DESC
            """
        )
        rows = cur.fetchall()
        for method, cnt in rows:
            print(f"  {method:<25} {cnt:>7,}")
        print()
        print("=" * 60)


def main():
    conn = get_conn()
    try:
        run_report(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
