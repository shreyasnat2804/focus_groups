"""
Propagate self-disclosure demographic tags across posts by the same author.
Layer 3 of the demographic tagging pipeline.

Usage:
    python3 scripts/propagate_author_tags.py           # summary only
    python3 scripts/propagate_author_tags.py -v        # per-author detail
"""

import argparse

from focus_groups.db import get_conn
from focus_groups.author_propagation import propagate_author_tags


def main(verbose: bool = False) -> None:
    conn = get_conn()
    try:
        stats = propagate_author_tags(conn, verbose=verbose)
        print(
            f"Done. {stats['authors_processed']:,} authors processed, "
            f"{stats['tags_inserted']:,} tags inserted, "
            f"{stats['authors_skipped_conflict']:,} authors had conflicting dimensions."
        )
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Propagate author self-disclosure tags to their other posts."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Print per-author detail.",
    )
    args = parser.parse_args()
    main(verbose=args.verbose)
