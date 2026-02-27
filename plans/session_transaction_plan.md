# Fix: Wrap Multi-step Session Operations in Transactions

**Status: IMPLEMENTED** (2026-02-27)

## Problem
The `create_session_endpoint` in `api.py` performs a multi-step sequence with individual commits at each step:

```
1. create_session(conn, ...)   → INSERT into sessions → conn.commit()
2. run_focus_group(...)        → Claude API calls (external, may fail)
3. save_responses(conn, ...)   → INSERT into responses → conn.commit()
4. complete_session(conn, ...) → UPDATE status → conn.commit()
```

If step 2 or 3 fails after step 1 succeeds, you get an **orphaned session** in `pending` status with no responses. The `except` block does call `fail_session()`, which marks it as `failed` — so it's not *completely* unhandled. But there are gaps:

- If `fail_session()` itself fails (e.g., the DB connection dropped mid-request), the session is stuck in `pending` forever
- The `rerun_session_endpoint` has a worse version: it calls `update_session_question()` + `delete_responses()` first, each with their own commit. If the subsequent `run_focus_group()` fails, the old question and responses are already gone — the session is left in a corrupted state with a new question, no responses, and `failed` status

### The rerun race condition in detail

```
rerun_session_endpoint:
1. update_session_question(conn, session_id, req.question)  → commits new question
2. delete_responses(conn, session_id)                         → commits deletion of old responses
3. select_personas(conn, ...)                                 → may fail (no matching personas)
4. run_focus_group(...)                                       → may fail (Claude API error)
5. save_responses(conn, ...)                                  → may fail
6. complete_session(conn, ...)                                → may fail
```

If step 4 fails: the old question is gone, old responses are gone, and you can't recover. The `except` block marks it as `failed`, but the original data is lost.

## Severity: MEDIUM-HIGH

## Approach: Deferred Commits with Rollback

Remove `conn.commit()` from individual session/response functions and let the API endpoint control the transaction boundary. On success, commit once. On failure, rollback to undo everything atomically.

This requires changes at two layers:
1. **`sessions.py`** — remove `conn.commit()` from all functions (let caller manage transactions)
2. **`api.py`** — add explicit `conn.commit()` / `conn.rollback()` in endpoint handlers

### Why not use psycopg2 autocommit?
Psycopg2 defaults to transaction mode (autocommit=False), which is exactly what we want. Each `execute()` is part of an implicit transaction until `commit()` or `rollback()`. We just need to stop committing prematurely.

## Changes

### 1. Update `src/focus_groups/sessions.py` — Remove all `conn.commit()` calls

Every function currently calls `conn.commit()` at the end. Remove all of them and add a docstring note that callers must commit.

Functions to change:
| Function | Line | Change |
|---|---|---|
| `create_session` | 35 | Remove `conn.commit()` |
| `save_responses` | 69 | Remove `conn.commit()` |
| `complete_session` | 84 | Remove `conn.commit()` |
| `fail_session` | 98 | **KEEP** `conn.commit()` — this is called from error handlers and must persist |
| `update_session_question` | 253 | Remove `conn.commit()` |
| `update_session_name` | 267 | Remove `conn.commit()` |
| `delete_responses` | 280 | Remove `conn.commit()` |
| `soft_delete_session` | 294 | Remove `conn.commit()` |
| `restore_session` | 308 | Remove `conn.commit()` |
| `purge_expired_sessions` | 320 | **KEEP** `conn.commit()` — called standalone from the purge timer |
| `permanently_delete_session` | 333 | Remove `conn.commit()` |

**Exception**: `fail_session` and `purge_expired_sessions` keep their commits because they are called from contexts where the surrounding transaction is already in an error state or they run independently.

Add a module-level docstring:

```python
"""
Session storage for focus group runs.

CRUD operations for focus_group_sessions and focus_group_responses tables.

IMPORTANT: Most functions do NOT commit. The caller (API endpoint) is
responsible for calling conn.commit() after all operations succeed,
or conn.rollback() on failure. Exceptions:
  - fail_session: commits immediately (called from error handlers)
  - purge_expired_sessions: commits immediately (runs standalone)
"""
```

### 2. Update `src/focus_groups/api.py` — Add transaction management

#### `create_session_endpoint`

```python
@api_router.post("/sessions", response_model=SessionCreated)
@limiter.limit("5/minute")
def create_session_endpoint(request: Request, req: SessionRequest, conn=Depends(get_db)):
    demo_filter = req.demographic_filter or {}

    cards = select_personas(
        conn,
        demographic_filter=demo_filter,
        sector=req.sector,
        n=req.num_personas,
    )

    if not cards:
        raise HTTPException(status_code=404, detail="No personas found matching the given filters.")

    session_id = create_session(
        conn,
        sector=req.sector,
        demographic_filter=demo_filter,
        num_personas=req.num_personas,
        question=req.question,
    )

    try:
        client = get_client()
        responses = run_focus_group(client, cards, req.question)
        save_responses(conn, session_id, responses)
        complete_session(conn, session_id)
        conn.commit()  # <-- single commit after all DB ops succeed
    except Exception:
        conn.rollback()  # <-- undo create_session + any partial saves
        logger.exception("Focus group generation failed")
        # fail_session commits independently
        fail_session(conn, session_id)
        raise HTTPException(status_code=500, detail="Focus group generation failed. Please try again.")

    return SessionCreated(
        session_id=session_id,
        status="completed",
        num_responses=len(responses),
    )
```

**Wait — there's a subtlety.** If we rollback, the `create_session` INSERT is undone, so `fail_session` would try to UPDATE a session that doesn't exist. We need to handle this.

**Revised approach for create**: commit the session creation first (so `fail_session` can find it), then wrap the rest in a transaction:

```python
def create_session_endpoint(request: Request, req: SessionRequest, conn=Depends(get_db)):
    demo_filter = req.demographic_filter or {}

    cards = select_personas(conn, demographic_filter=demo_filter, sector=req.sector, n=req.num_personas)
    if not cards:
        raise HTTPException(status_code=404, detail="No personas found matching the given filters.")

    # Create session and commit — must exist for fail_session to work
    session_id = create_session(conn, sector=req.sector, demographic_filter=demo_filter,
                                 num_personas=req.num_personas, question=req.question)
    conn.commit()

    try:
        client = get_client()
        responses = run_focus_group(client, cards, req.question)
        save_responses(conn, session_id, responses)
        complete_session(conn, session_id)
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Focus group generation failed")
        fail_session(conn, session_id)  # commits independently
        raise HTTPException(status_code=500, detail="Focus group generation failed. Please try again.")

    return SessionCreated(session_id=session_id, status="completed", num_responses=len(responses))
```

This is actually very close to the current behavior. The real win is on **rerun**.

#### `rerun_session_endpoint` — THE CRITICAL FIX

This is where the transaction boundary matters most. Currently, `update_session_question` and `delete_responses` commit immediately, destroying the old data before we know if the rerun will succeed.

```python
@api_router.post("/sessions/{session_id}/rerun", response_model=SessionCreated)
@limiter.limit("5/minute")
def rerun_session_endpoint(request: Request, session_id: str, req: RerunRequest, conn=Depends(get_db)):
    session = get_session(conn, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    sector = req.sector if req.sector is not None else session["sector"]
    num_personas = req.num_personas if req.num_personas is not None else session["num_personas"]
    demo_filter = req.demographic_filter if req.demographic_filter is not None else (session["demographic_filter"] or {})

    cards = select_personas(conn, demographic_filter=demo_filter, sector=sector, n=num_personas)
    if not cards:
        raise HTTPException(status_code=404, detail="No personas found matching the given filters.")

    try:
        # Run Claude FIRST, before modifying any DB state
        client = get_client()
        responses = run_focus_group(client, cards, req.question)

        # All Claude calls succeeded — now update DB atomically
        update_session_question(conn, session_id, req.question)
        delete_responses(conn, session_id)
        save_responses(conn, session_id, responses)
        complete_session(conn, session_id)
        conn.commit()  # <-- atomic: question + responses + status all committed together
    except Exception:
        conn.rollback()  # <-- old question and responses are preserved!
        logger.exception("Focus group re-run failed")
        fail_session(conn, session_id)
        raise HTTPException(status_code=500, detail="Focus group re-run failed. Please try again.")

    return SessionCreated(session_id=session_id, status="completed", num_responses=len(responses))
```

**Key change**: Claude API calls happen **before** any DB mutations. If Claude fails, we rollback and the original session data is untouched. This completely eliminates the data-loss race condition.

#### Other single-operation endpoints

For endpoints that do a single DB operation (delete, restore, rename), add a commit after the call since `sessions.py` no longer commits:

```python
@api_router.delete("/sessions/{session_id}")
@limiter.limit("20/minute")
def delete_session_endpoint(request: Request, session_id: str, conn=Depends(get_db)):
    session = get_session(conn, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    soft_delete_session(conn, session_id)
    conn.commit()
    return {"status": "deleted", "session_id": session_id}
```

Same pattern for: `restore_session_endpoint`, `permanently_delete_session_endpoint`, `rename_session_endpoint`.

### 3. Update `src/focus_groups/db.py`

Any function in `db.py` that does `conn.commit()` should be audited. From the grep results, line 129, 201, 221, 458 have commits. These are likely in data loading/scraping functions that run standalone — they should **keep** their commits since they're not called from API endpoints.

No changes needed in `db.py`.

## Tests

### `tests/test_session_transactions.py`

```python
"""Tests for transactional integrity of session operations."""

from unittest.mock import MagicMock, patch, call
from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def tx_client():
    """Client that tracks commit/rollback calls on the connection."""
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock()
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with (
        patch("focus_groups.api.init_pool"),
        patch("focus_groups.api.close_pool"),
        patch("focus_groups.api.get_pool_conn", return_value=mock_conn),
        patch("focus_groups.api.return_pool_conn"),
        patch("focus_groups.api.select_personas") as mock_select,
        patch("focus_groups.api.get_client") as mock_get_client,
        patch("focus_groups.api.run_focus_group") as mock_run,
        patch("focus_groups.api.get_session") as mock_get_session,
    ):
        from focus_groups.personas.cards import PersonaCard
        from focus_groups.api import app, get_db

        mock_select.return_value = [
            PersonaCard(post_id=1, demographic_tags={"age_group": "25-34"}, text_excerpt="Test", sector="tech"),
        ]
        mock_get_client.return_value = MagicMock()

        now = "2026-02-27T10:00:00+00:00"
        mock_get_session.return_value = {
            "id": "sess-1", "sector": "tech", "demographic_filter": {},
            "question": "Old question?", "num_personas": 1,
            "status": "completed", "created_at": now, "completed_at": now,
            "name": None,
            "responses": [{"post_id": 1, "response_text": "Old response", "persona_summary": "25-34"}],
        }

        app.dependency_overrides[get_db] = lambda: mock_conn
        client = TestClient(app)

        yield client, mock_conn, mock_run

        app.dependency_overrides.clear()


class TestRerunTransaction:
    """Verify rerun endpoint preserves data on failure."""

    def test_successful_rerun_commits_once(self, tx_client):
        client, mock_conn, mock_run = tx_client
        mock_run.return_value = [
            {"post_id": 1, "persona_summary": "25-34", "system_prompt": "...", "response_text": "New", "model": "m"},
        ]
        # Reset commit tracking
        mock_conn.commit.reset_mock()

        resp = client.post("/api/sessions/sess-1/rerun", json={"question": "New Q?"})
        assert resp.status_code == 200

        # Should commit (session creation commit is separate, rerun does one commit for the update batch)
        assert mock_conn.commit.called

    def test_claude_failure_triggers_rollback(self, tx_client):
        client, mock_conn, mock_run = tx_client
        mock_run.side_effect = Exception("Claude API timeout")
        mock_conn.commit.reset_mock()
        mock_conn.rollback.reset_mock()

        resp = client.post("/api/sessions/sess-1/rerun", json={"question": "New Q?"})
        assert resp.status_code == 500

        # Should rollback, preserving old question + responses
        assert mock_conn.rollback.called


class TestCreateTransaction:
    """Verify create endpoint handles failures correctly."""

    def test_claude_failure_marks_session_failed(self, tx_client):
        client, mock_conn, mock_run = tx_client
        mock_run.side_effect = Exception("Claude API error")

        # Mock cursor to return a session ID
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = ("new-sess-id",)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        resp = client.post("/api/sessions", json={
            "question": "Test?", "num_personas": 1, "sector": "tech",
        })
        assert resp.status_code == 500
        assert mock_conn.rollback.called
```

## Files Touched
- `src/focus_groups/sessions.py` (remove `conn.commit()` from most functions, update docstrings)
- `src/focus_groups/api.py` (add `conn.commit()` / `conn.rollback()` in endpoints, reorder rerun logic)
- `tests/test_session_transactions.py` (new)
- `tests/test_api.py` (may need adjustments if mocking behavior changes)

## Migration Risk
- **Low risk**: psycopg2 already uses transaction mode by default. We're just moving commit points, not changing isolation levels.
- **Watch for**: any code path that reads data written in the same transaction before commit — this works fine in psycopg2 (read-your-writes within a transaction) but verify in tests.
- **`fail_session` keeps its own commit**: this is critical. After a rollback, the connection is clean and `fail_session` starts a new implicit transaction, commits it, and the failure status persists.
