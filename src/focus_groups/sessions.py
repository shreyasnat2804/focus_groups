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
) -> int:
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
        session_id = cur.fetchone()[0]
    conn.commit()
    return session_id


def save_responses(conn, session_id: int, responses: list[dict]) -> int:
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


def complete_session(conn, session_id: int) -> None:
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


def fail_session(conn, session_id: int) -> None:
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


def get_session(conn, session_id: int) -> dict | None:
    """
    Fetch a session with all its responses.

    Returns None if the session doesn't exist.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, sector, demographic_filter, question,
                   num_personas, status, created_at, completed_at
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


def list_sessions(conn, limit: int = 20) -> list[dict]:
    """Return recent sessions (without responses) ordered by newest first."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, sector, question, num_personas, status, created_at
            FROM focus_group_sessions
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "sector": r[1],
            "question": r[2],
            "num_personas": r[3],
            "status": r[4],
            "created_at": r[5],
        }
        for r in rows
    ]
