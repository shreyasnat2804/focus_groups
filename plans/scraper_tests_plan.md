# Fix: Add Scraper Tests

## Problem
`scraper.py` (358 lines) is the most complex module with retry logic, rate limiting, deduplication, region mapping, and pagination — all with zero test coverage.

## Severity: CRITICAL

## Test Plan: `tests/test_scraper.py`

### Unit Tests

#### `fetch_json()`
- **Network error retry**: Mock `session.get` to raise `RequestException` twice then succeed. Verify 3 retries with exponential backoff (mock `time.sleep` to verify 1s, 2s delays).
- **429 rate limit**: Mock 429 response with `Retry-After: 5` header. Verify it waits and retries. **Verify it increments `attempt`** (this is the unbounded recursion bug — currently it passes `attempt` unchanged).
- **403/404 skip**: Mock 403 response. Verify returns `None`, no retry.
- **500 server error retry**: Mock 500 twice then 200. Verify retries up to 4 times.
- **Max retries exhausted**: Mock persistent network errors. Verify returns `None` after 3 attempts.
- **Bad JSON**: Mock 200 response with invalid JSON body. Verify returns `None`.

#### `iter_subreddit()`
- **Basic pagination**: Mock 2 pages of Reddit JSON with valid posts. Verify all qualifying posts yielded.
- **Post filtering**: Provide posts below `MIN_SCORE`, short body, deleted author, empty body. Verify all filtered out.
- **Date cutoff**: Provide posts before and after `min_date`. Verify posts before cutoff skipped, pagination stops after cutoff page.
- **Deduplication**: Not handled here (handled in `run()`), but verify the generator yields even duplicates.
- **Empty page stops**: Mock a page with no children. Verify pagination stops.
- **No `after` cursor stops**: Mock page without `after` field. Verify pagination stops.

#### `SUBREDDIT_REGIONS`
- Verify all subreddits listed in `SUBREDDITS` that have a region mapping are correctly represented.
- Verify subreddits without a mapping return `None` as region.

#### `run()`
- **JSONL dedup**: Create temp JSONL with existing IDs. Verify `run()` skips those IDs.
- **DB insert path**: Mock DB connection + `insert_posts`. Verify posts inserted.
- **DB unavailable path**: Mock `_try_get_db_conn` returning None. Verify JSONL-only mode works.
- **Probe mode**: Verify only first subreddit per sector is scraped, max 1 page.

### Bug Fix: Unbounded Recursion on 429

In `fetch_json` line 128: `return fetch_json(url, session, attempt)` — `attempt` is not incremented. If the server keeps returning 429, this recurses forever until stack overflow.

**Fix**: Add a max retry count for 429s:
```python
if resp.status_code == 429:
    if attempt >= 5:
        print("  [429] max retries exceeded")
        return None
    wait = int(resp.headers.get("Retry-After", 60))
    print(f"  [429] rate limited — waiting {wait}s")
    time.sleep(wait)
    return fetch_json(url, session, attempt + 1)
```

## Files Touched
- `tests/test_scraper.py` (new, ~200 lines)
- `src/focus_groups/scraper.py` (fix 429 retry bug on line 128)
