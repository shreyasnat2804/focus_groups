# Fix: Restrict CORS

## Problem
`allow_origins=["*"]` combined with `allow_credentials=True` is contradictory (browsers ignore credentials with wildcard origin) and dangerous if credentials are ever added.

## Severity: HIGH

## Changes

### 1. Update `api.py` CORS configuration

```python
import os

ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000"  # Vite dev default
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)
```

- Dev: defaults to `localhost:5173` (Vite) and `localhost:3000`
- Prod: set `CORS_ORIGINS` env var to the actual frontend domain
- Explicitly list allowed methods and headers instead of wildcard

### 2. Document in `.env.example`
```
CORS_ORIGINS=https://your-frontend.run.app
```

## Tests
- Verify CORS headers in responses match configured origins
- Verify requests from non-allowed origins are rejected

## Files Touched
- `src/focus_groups/api.py` (update middleware config)
- `.env.example` (document)
