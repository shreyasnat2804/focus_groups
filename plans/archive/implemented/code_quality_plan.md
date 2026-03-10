# Fix: Code Quality Issues ✅ IMPLEMENTED

## Problem
Multiple code quality issues identified:
1. Unbounded recursion in `fetch_json` on 429 responses (covered in scraper_tests_plan.md)
2. `insert_tags` raises unhandled `KeyError` on unknown dimension/value pairs
3. `purge_expired_sessions` called on every GET `/api/sessions` request
4. Duplicated `_load_wtp_template` across two files
5. Hardcoded Claude model/token limits
6. Sequential Claude API calls (50 personas = 50 serial round-trips)
7. `ORDER BY RANDOM()` on large tables

## Severity: HIGH (KeyError crash, sequential calls) + MEDIUM (rest)

## Changes

### 1. Handle unknown tags in `insert_tags` (`db.py:383-391`)

Currently `value_ids[(t["dimension"], t["value"])]` raises `KeyError` if the dimension/value pair isn't in the DB lookup table. Fix:

```python
rows = []
skipped = 0
for t in tags:
    key = (t["dimension"], t["value"])
    vid = value_ids.get(key)
    if vid is None:
        skipped += 1
        continue
    rows.append((t["post_id"], vid, t["confidence"], t["method"]))

if skipped:
    import logging
    logging.getLogger(__name__).warning(f"Skipped {skipped} tags with unknown dimension/value")
```

### 2. Move `purge_expired_sessions` to a background task

Currently called on every `GET /api/sessions` request (line 222). This is a DELETE operation on every read — wasteful and surprising.

Options:
- **Simple**: Run purge only if a flag/interval has passed (check a module-level timestamp)
- **Better**: Run as a FastAPI background task on startup + periodic
- **Simplest for now**: Move to a separate endpoint or CLI command, remove from GET

Recommended approach — interval-based:
```python
import time
_last_purge = 0
PURGE_INTERVAL = 3600  # 1 hour

@app.get("/api/sessions")
def list_sessions_endpoint(..., conn=Depends(get_db)):
    global _last_purge
    if time.time() - _last_purge > PURGE_INTERVAL:
        purge_expired_sessions(conn)
        _last_purge = time.time()
    ...
```

### 3. Deduplicate `_load_wtp_template`

Both `wtp/van_westendorp.py` and `personas/profiles.py` have their own `_load_wtp_template` / `load_prompt_template`. They differ only in the directory they look in.

Leave as-is — they serve different directories (`wtp/prompts/` vs `prompts/`), so deduplication would add coupling for minimal benefit. Document this decision.

### 4. Extract Claude model config

Currently hardcoded in `claude.py`. Extract to constants or env vars:

```python
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "1024"))
```

### 5. Parallel Claude API calls (future enhancement)

50 serial round-trips is slow. Use `asyncio.gather` or `concurrent.futures.ThreadPoolExecutor`:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_focus_group(client, cards, question, max_workers=5):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_single, client, card, question): card
            for card in cards
        }
        results = []
        for future in as_completed(futures):
            results.append(future.result())
    return results
```

Cap at 5 concurrent to respect Claude rate limits. This is a larger refactor — plan separately if desired.

### 6. `ORDER BY RANDOM()` optimization (`db.py:230`)

For tables under 100K rows, `ORDER BY RANDOM()` is acceptable. For larger tables, use `TABLESAMPLE SYSTEM` or a two-pass approach. Current scale (30K posts target) is fine — add a comment noting the tradeoff and revisit if data grows 10x+.

## Files Touched
- `src/focus_groups/db.py` (fix KeyError in insert_tags)
- `src/focus_groups/api.py` (throttle purge_expired_sessions)
- `src/focus_groups/claude.py` (extract model config to env vars)
- `src/focus_groups/scraper.py` (429 fix — covered in scraper_tests_plan.md)
