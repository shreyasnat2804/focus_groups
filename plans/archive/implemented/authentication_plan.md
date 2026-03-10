# Fix: Add API Authentication ✅ IMPLEMENTED

## Problem
No authentication on any API endpoint. Anyone who discovers the API URL can create sessions (triggering paid Claude API calls), delete all data, and export everything. Combined with no rate limiting and unbounded `num_personas`, this is a direct cost-amplification attack vector.

## Severity: CRITICAL

## Approach: API Key Middleware

Use a simple API key scheme via `X-API-Key` header. This is appropriate for a single-user/internal-team tool. OAuth would be overkill at this stage.

## Changes

### 1. Create `src/focus_groups/auth.py`
```python
"""API key authentication middleware."""
import os
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key():
    """Read API key from environment."""
    key = os.getenv("FG_API_KEY")
    if not key:
        # No key configured = auth disabled (local dev)
        return None
    return key

async def require_api_key(api_key: str = Security(API_KEY_HEADER)):
    """FastAPI dependency that validates the API key."""
    expected = get_api_key()
    if expected is None:
        return  # Auth disabled
    if not api_key or api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
```

### 2. Update `api.py`
- Import `require_api_key` from `auth.py`
- Add as a global dependency on the app: `app = FastAPI(..., dependencies=[Depends(require_api_key)])`
- This protects all endpoints with a single line

### 3. Update frontend `api.js`
- Read API key from env/config: `const API_KEY = import.meta.env.VITE_API_KEY`
- Add `X-API-Key` header to all fetch calls
- Create a shared `fetchWithAuth()` wrapper to avoid repetition

### 4. Environment
- Add `FG_API_KEY` to `.env.example`
- Add `VITE_API_KEY` to frontend `.env.example`
- Document in CLAUDE.md

## Tests
- `test_auth.py`: verify 401 without key, 200 with valid key, 401 with wrong key
- Test that auth is disabled when `FG_API_KEY` is not set (local dev convenience)
- Update existing `test_api.py` to include API key header in requests

## Files Touched
- `src/focus_groups/auth.py` (new)
- `src/focus_groups/api.py` (add dependency)
- `frontend/src/api.js` (add header)
- `tests/test_auth.py` (new)
- `tests/test_api.py` (update fixtures)
- `.env.example` (document key)
