"""
Migration: add unique index on demographic_tags(post_id, dimension, method).
Required for ON CONFLICT DO NOTHING in insert_tags().
Run once against the live Docker DB:
    python3 scripts/migrate_tags_unique_index.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import get_conn

SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_tags_unique
    ON demographic_tags(post_id, dimension, method);
"""


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(SQL)
        conn.commit()
        print("Migration applied: idx_tags_unique created (or already existed).")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
