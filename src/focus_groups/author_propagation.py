"""
Author history tag propagation (Layer 3).

For authors with multiple posts, propagate self-disclosure tags to their
other posts that lack those dimensions. Only propagates dimensions where
the author has a single consistent value across all self-disclosure tags.

Usage:
    from focus_groups.author_propagation import propagate_author_tags
    stats = propagate_author_tags(conn, verbose=True)
"""

from focus_groups.db import (
    get_authors_with_multiple_posts,
    insert_tags,
    load_demographic_value_ids,
)

AUTHOR_HISTORY_CONFIDENCE = 0.75
AUTHOR_HISTORY_METHOD = "author_history"


def _get_self_disclosure_tags(conn, author: str) -> list[tuple[str, str, int]]:
    """
    Return self-disclosure tags for an author grouped by dimension.
    Returns [(dimension, value, post_count), ...].
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT dd.name AS dimension, dv.value, COUNT(DISTINCT p.id) AS post_count
            FROM posts p
            JOIN demographic_tags dt ON dt.post_id = p.id
            JOIN demographic_values dv ON dv.id = dt.demographic_value_id
            JOIN demographic_dimensions dd ON dd.id = dv.dimension_id
            WHERE p.author = %s
              AND dt.method = 'self_disclosure'
            GROUP BY dd.name, dv.value
            """,
            (author,),
        )
        return cur.fetchall()


def _get_untagged_posts_for_dimension(conn, author: str, dimension: str) -> list[int]:
    """
    Return post IDs for an author that don't have any tag for the given dimension.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.id FROM posts p
            WHERE p.author = %s
              AND NOT EXISTS (
                SELECT 1 FROM demographic_tags dt
                JOIN demographic_values dv ON dv.id = dt.demographic_value_id
                JOIN demographic_dimensions dd ON dd.id = dv.dimension_id
                WHERE dt.post_id = p.id AND dd.name = %s
              )
            """,
            (author, dimension),
        )
        return [row[0] for row in cur.fetchall()]


def propagate_author_tags(conn, verbose: bool = False) -> dict:
    """
    Propagate self-disclosure tags across all posts by the same author.

    For each author with 2+ posts:
    - Collect all self-disclosure tags
    - For each dimension with a single consistent value, propagate to untagged posts
    - Skip dimensions with conflicting values

    Returns stats dict: {authors_processed, tags_inserted, authors_skipped_conflict}
    """
    authors = get_authors_with_multiple_posts(conn)
    value_ids = load_demographic_value_ids(conn)

    stats = {
        "authors_processed": 0,
        "tags_inserted": 0,
        "authors_skipped_conflict": 0,
    }

    for author in authors:
        disclosure_tags = _get_self_disclosure_tags(conn, author)

        if not disclosure_tags:
            continue

        # Group by dimension: {dimension: set of values}
        dim_values: dict[str, set[str]] = {}
        for dimension, value, _count in disclosure_tags:
            dim_values.setdefault(dimension, set()).add(value)

        tags_to_insert = []
        had_conflict = False

        for dimension, values in dim_values.items():
            if len(values) > 1:
                # Conflicting values — skip this dimension
                had_conflict = True
                if verbose:
                    print(f"  {author}: SKIP {dimension} (conflicting: {values})")
                continue

            value = next(iter(values))
            untagged_post_ids = _get_untagged_posts_for_dimension(conn, author, dimension)

            for post_id in untagged_post_ids:
                tags_to_insert.append({
                    "post_id": post_id,
                    "dimension": dimension,
                    "value": value,
                    "confidence": AUTHOR_HISTORY_CONFIDENCE,
                    "method": AUTHOR_HISTORY_METHOD,
                })

        if had_conflict:
            stats["authors_skipped_conflict"] += 1

        if tags_to_insert:
            n = insert_tags(conn, tags_to_insert, value_ids=value_ids)
            stats["tags_inserted"] += n
            if verbose:
                print(f"  {author}: inserted {n} tags across {len(tags_to_insert)} post-dimensions")

        stats["authors_processed"] += 1

    return stats
