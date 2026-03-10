# Fix: Add Rate Limiting ✅ IMPLEMENTED

## Problem
No rate limiting on any endpoint. Claude-calling endpoints (`POST /api/sessions`, `POST .../rerun`, `POST .../wtp`) can be spammed indefinitely, running up API costs.

## Severity: HIGH

## Approach: slowapi

Use `slowapi` (built on top of `limits`), the standard FastAPI rate limiting library. It integrates as middleware and uses client IP for identification.

## Changes

### 1. Add dependency
- Add `slowapi>=0.1.9` to `pyproject.toml` dependencies

### 2. Update `api.py`

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

Rate limits per endpoint:
| Endpoint | Limit | Rationale |
|----------|-------|-----------|
| `POST /api/sessions` | 5/minute | Triggers Claude calls |
| `POST .../rerun` | 5/minute | Triggers Claude calls |
| `POST .../wtp` | 5/minute | Triggers Claude calls |
| `GET /api/sessions` | 30/minute | Read-only, lightweight |
| `GET .../export/*` | 10/minute | Read-only, some compute |
| `DELETE`, `PATCH`, `POST restore` | 20/minute | Lightweight mutations |

Apply with `@limiter.limit("5/minute")` decorator on each endpoint.

### 3. Configuration
- Rate limits configurable via env vars (optional enhancement)
- Default to the above if not set

## Tests
- `test_rate_limiting.py`: send requests exceeding the limit, verify 429 response
- Test that rate limit headers are included in responses

## Files Touched
- `pyproject.toml` (add slowapi)
- `src/focus_groups/api.py` (add limiter middleware + decorators)
- `tests/test_rate_limiting.py` (new)
