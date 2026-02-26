"""
Session storage for focus group runs.

CRUD operations for focus_group_sessions and focus_group_responses tables.
"""

from __future__ import annotations

from psycopg2.extras import Json


def create_session(
    conn,
    sector: str | None,
    demographic_filter: dict,
    num_personas: int,
    question: str,
) -> str:
    """
    Insert a new focus group session and return its id.

    The session starts in 'pending' status.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO focus_group_sessions
                (sector, demographic_filter, question, num_personas, status)
            VALUES (%s, %s, %s, %s, 'pending')
            RETURNING id
            """,
            (sector, Json(demographic_filter), question, num_personas),
        )
        session_id = str(cur.fetchone()[0])
    conn.commit()
    return session_id


def save_responses(conn, session_id: str, responses: list[dict]) -> int:
    """
    Bulk-insert focus group responses for a session.

    Each response dict must have:
      post_id, persona_summary, system_prompt, response_text, model

    Returns number of rows inserted.
    """
    if not responses:
        return 0

    with conn.cursor() as cur:
        for r in responses:
            cur.execute(
                """
                INSERT INTO focus_group_responses
                    (session_id, post_id, persona_summary, system_prompt, response_text, model)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    session_id,
                    r["post_id"],
                    r["persona_summary"],
                    r["system_prompt"],
                    r["response_text"],
                    r["model"],
                ),
            )

    conn.commit()
    return len(responses)


def complete_session(conn, session_id: str) -> None:
    """Mark a session as completed with a timestamp."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE focus_group_sessions
            SET status = 'completed', completed_at = NOW()
            WHERE id = %s
            """,
            (session_id,),
        )
    conn.commit()


def fail_session(conn, session_id: str) -> None:
    """Mark a session as failed."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE focus_group_sessions
            SET status = 'failed', completed_at = NOW()
            WHERE id = %s
            """,
            (session_id,),
        )
    conn.commit()


def get_session(conn, session_id: str) -> dict | None:
    """
    Fetch a session with all its responses.

    Returns None if the session doesn't exist.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, sector, demographic_filter, question,
                   num_personas, status, created_at, completed_at, name
            FROM focus_group_sessions
            WHERE id = %s
            """,
            (session_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, post_id, persona_summary, system_prompt,
                   response_text, model, created_at
            FROM focus_group_responses
            WHERE session_id = %s
            ORDER BY id
            """,
            (session_id,),
        )
        response_rows = cur.fetchall()

    return {
        "id": row[0],
        "sector": row[1],
        "demographic_filter": row[2],
        "question": row[3],
        "num_personas": row[4],
        "status": row[5],
        "created_at": row[6],
        "completed_at": row[7],
        "name": row[8],
        "responses": [
            {
                "id": r[0],
                "post_id": r[1],
                "persona_summary": r[2],
                "system_prompt": r[3],
                "response_text": r[4],
                "model": r[5],
                "created_at": r[6],
            }
            for r in response_rows
        ],
    }


def _build_filter_clause(
    search: str | None = None,
    sector: str | None = None,
    deleted: bool = False,
) -> tuple[str, list]:
    """Build WHERE clause and params for search/sector/deleted filters."""
    conditions = []
    params: list = []

    if deleted:
        conditions.append(
            "deleted_at IS NOT NULL AND deleted_at > NOW() - INTERVAL '30 days'"
        )
    else:
        conditions.append("deleted_at IS NULL")

    if search:
        conditions.append("question ILIKE %s")
        params.append(f"%{search}%")

    if sector:
        conditions.append("sector = %s")
        params.append(sector)

    where = " AND ".join(conditions)
    return where, params


def list_sessions(
    conn,
    limit: int = 10,
    offset: int = 0,
    search: str | None = None,
    sector: str | None = None,
    deleted: bool = False,
) -> list[dict]:
    """Return recent sessions (without responses) ordered by newest first."""
    where, params = _build_filter_clause(search=search, sector=sector, deleted=deleted)
    query = f"""
        SELECT id, sector, question, num_personas, status, created_at, deleted_at, name
        FROM focus_group_sessions
        WHERE {where}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(query, tuple(params))
        rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "sector": r[1],
            "question": r[2],
            "num_personas": r[3],
            "status": r[4],
            "created_at": r[5],
            "deleted_at": r[6],
            "name": r[7],
        }
        for r in rows
    ]


def count_sessions(
    conn,
    search: str | None = None,
    sector: str | None = None,
    deleted: bool = False,
) -> int:
    """Return total number of sessions matching filters."""
    where, params = _build_filter_clause(search=search, sector=sector, deleted=deleted)
    query = f"SELECT COUNT(*) FROM focus_group_sessions WHERE {where}"

    with conn.cursor() as cur:
        cur.execute(query, tuple(params))
        return cur.fetchone()[0]


def update_session_question(conn, session_id: str, question: str) -> None:
    """Update the question field for a session."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE focus_group_sessions
            SET question = %s
            WHERE id = %s
            """,
            (question, session_id),
        )
    conn.commit()


def update_session_name(conn, session_id: str, name: str | None) -> None:
    """Update the display name for a session. Pass None to clear it."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE focus_group_sessions
            SET name = %s
            WHERE id = %s
            """,
            (name, session_id),
        )
    conn.commit()


def delete_responses(conn, session_id: str) -> None:
    """Delete all responses for a session."""
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM focus_group_responses
            WHERE session_id = %s
            """,
            (session_id,),
        )
    conn.commit()


def soft_delete_session(conn, session_id: str) -> None:
    """Soft delete a session by setting deleted_at to now."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE focus_group_sessions
            SET deleted_at = NOW()
            WHERE id = %s
            """,
            (session_id,),
        )
    conn.commit()


def restore_session(conn, session_id: str) -> None:
    """Restore a soft-deleted session by clearing deleted_at."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE focus_group_sessions
            SET deleted_at = NULL
            WHERE id = %s
            """,
            (session_id,),
        )
    conn.commit()


def purge_expired_sessions(conn) -> None:
    """Permanently delete sessions that were soft-deleted more than 30 days ago."""
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM focus_group_sessions
            WHERE deleted_at < NOW() - INTERVAL '30 days'
            """
        )
    conn.commit()


def permanently_delete_session(conn, session_id: str) -> None:
    """Permanently delete a session (hard delete)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM focus_group_sessions
            WHERE id = %s
            """,
            (session_id,),
        )
    conn.commit()
