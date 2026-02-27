# Fix: Sanitize Error Responses — IMPLEMENTED

## Problem
Exception details are leaked to clients via `HTTPException(detail=f"...{e}")`. Internal tracebacks are printed to stdout. This exposes implementation details to attackers.

## Severity: HIGH

## Locations
- `api.py:184` — `f"Focus group generation failed: {e}"`
- `api.py:344` — `f"Focus group re-run failed: {e}"`
- `api.py:451` — `f"WTP analysis failed: {e}"`
- `api.py:181-182, 341-342, 449-450` — `traceback.print_exc()`

## Changes

### 1. Replace exception detail strings with generic messages

```python
except Exception as e:
    logger.exception("Focus group generation failed")
    fail_session(conn, session_id)
    raise HTTPException(status_code=500, detail="Focus group generation failed. Please try again.")
```

### 2. Add proper logging

```python
import logging
logger = logging.getLogger(__name__)
```

Replace all `traceback.print_exc()` with `logger.exception(...)` — this still logs the full traceback server-side but doesn't expose it to the client.

### 3. Add a global exception handler (optional hardening)

```python
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
```

## Changes Summary
| Line | Before | After |
|------|--------|-------|
| 181-184 | `traceback.print_exc()` + `detail=f"...{e}"` | `logger.exception(...)` + generic message |
| 341-344 | same | same |
| 449-451 | same | same |

## Tests
- Verify 500 responses contain generic messages, not exception details
- Verify server logs contain the actual exception (check log capture)

## Files Touched
- `src/focus_groups/api.py` (replace all 3 error handlers + add logging)
