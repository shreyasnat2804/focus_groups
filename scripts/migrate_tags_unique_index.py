"""
Migration: add unique index on demographic_tags(post_id, dimension, method).
Required for ON CONFLICT DO NOTHING in insert_tags().
Run once against the live Docker DB:

Usage:
    python3 scripts/migrate_tags_unique_index.py      # silent on success
    python3 scripts/migrate_tags_unique_index.py -v   # confirm what was done
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_conn

SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_unique
    ON demographic_tags(post_id, dimension, method);
"""


def main(verbose: bool = False) -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(SQL)
        conn.commit()
        if verbose:
            print("Migration applied: idx_tags_unique on (post_id, dimension, method) — created or already existed.")
        else:
            print("Migration OK.")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply demographic_tags unique index migration.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print full confirmation message.")
    args = parser.parse_args()
    main(verbose=args.verbose)
