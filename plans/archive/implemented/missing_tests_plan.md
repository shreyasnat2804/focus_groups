# Fix: Add Missing Test Coverage ✅ IMPLEMENTED

## Problem
Several modules and endpoints have zero test coverage:
- `load_and_tag.py` (69 lines)
- `remove_megathreads.py` (79 lines)
- `personas/selection.py` (66 lines)
- DELETE, restore, permanent delete endpoints
- Input validation edge cases for existing endpoints

## Severity: HIGH

## Status: IMPLEMENTED (2026-02-26)

Tests 1–4 implemented (26 new tests, all passing). Item 5 (reduce over-mocking) deferred — current mocking pattern works and matches existing test_api.py conventions.

## Test Plans

### 1. `tests/test_load_and_tag.py`

Test `load_and_tag.py` which batch-loads JSONL posts into the DB and tags them:
- **Happy path**: Mock JSONL file with 3 posts, mock DB. Verify `insert_posts` called with correct batches, `insert_tags` called with tag rows.
- **Empty JSONL**: Verify no DB calls made.
- **Duplicate handling**: Verify `ON CONFLICT DO NOTHING` behavior (mock `insert_posts` returning 0).
- **Tagger failure**: Mock `tag_post` raising. Verify posts still inserted, error logged.
- **Batch sizing**: Provide 501 posts. Verify two batches of 500 + 1.

### 2. `tests/test_remove_megathreads.py`

Test megathread detection and removal:
- **Detection**: Provide posts with duplicate (subreddit, title) pairs. Verify correct IDs identified.
- **Postgres delete**: Mock cursor. Verify DELETE query with correct IDs.
- **JSONL rewrite**: Create temp JSONL with 5 posts, remove 2. Verify output file has 3 posts.
- **No megathreads**: Verify no delete if no duplicates found.

### 3. `tests/test_personas_selection.py`

Test `select_personas()` end-to-end (with mocked DB):
- **Happy path**: Mock `get_posts_with_embeddings` returning 10 posts. Verify N PersonaCards returned.
- **Fewer posts than requested**: Pool has 3 posts, request 10. Verify returns 3.
- **Empty pool**: No posts match. Verify returns empty list.
- **Demographic filter passthrough**: Verify filter dict passed to `get_posts_with_embeddings`.
- **Sector filter passthrough**: Verify sector passed through.

### 4. `tests/test_api_mutations.py`

Test the untested mutation endpoints:

#### DELETE `/api/sessions/{id}`
- Soft delete existing session → 200, verify `soft_delete_session` called
- Delete non-existent session → 404

#### POST `/api/sessions/{id}/restore`
- Restore deleted session → 200, verify `restore_session` called
- Restore non-existent session → 404

#### DELETE `/api/sessions/{id}/permanent`
- Permanently delete → 200, verify `permanently_delete_session` called
- Delete non-existent → 404

#### PATCH `/api/sessions/{id}/name`
- Rename session → 200, verify `update_session_name` called with correct args
- Rename to None (clear name) → 200
- Rename non-existent → 404

### 5. Reduce over-mocking in `test_api.py`

Current `test_api.py` uses 14 patches per test. Refactor to:
- Use FastAPI's dependency override for `get_db` (once connection pooling is added)
- Create shared fixtures for common mock setups
- Only mock at the boundary (DB layer), not intermediate functions

## Files Touched
- `tests/test_load_and_tag.py` (new)
- `tests/test_remove_megathreads.py` (new)
- `tests/test_personas_selection.py` (new)
- `tests/test_api_mutations.py` (new)
- `tests/test_api.py` (refactor mocking after connection pooling change)
