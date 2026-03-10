# Fix: Connection Leak + Connection Pooling

## Problem
1. **Connection leak**: In `create_session_endpoint` (line 151), `conn = get_conn()` is called before the `try/finally` block. If `select_personas()` (line 155) or `create_session()` (line 166) raises, the connection is never closed. Same pattern in `rerun_session_endpoint` and `run_wtp_endpoint`.
2. **No connection pooling**: Every request opens a new TCP connection via `get_conn()`.

## Severity: CRITICAL (leak) + HIGH (pooling)

## Approach: FastAPI Dependency with Connection Pool

Replace the manual `conn = get_conn()` / `try/finally/conn.close()` pattern across all endpoints with a single FastAPI dependency that yields a connection from a pool.

## Changes

### 1. Update `db.py` — Add connection pool

```python
from psycopg2.pool import ThreadedConnectionPool

_pool: ThreadedConnectionPool | None = None

def init_pool(minconn=2, maxconn=10):
    """Initialize the connection pool. Call once at startup."""
    global _pool
    _pool = ThreadedConnectionPool(
        minconn, maxconn,
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DB", "focusgroups"),
        user=os.getenv("PG_USER", "fg_user"),
        password=os.getenv("PG_PASSWORD", "localdev"),
    )

def get_pool_conn():
    """Get a connection from the pool."""
    conn = _pool.getconn()
    register_vector(conn)
    return conn

def return_pool_conn(conn):
    """Return a connection to the pool."""
    _pool.putconn(conn)

def close_pool():
    """Close all connections in the pool."""
    if _pool:
        _pool.closeall()
```

### 2. Update `api.py` — FastAPI dependency

```python
from fastapi import Depends

def get_db():
    """FastAPI dependency: yield a pooled connection, always returned."""
    conn = get_pool_conn()
    try:
        yield conn
    finally:
        return_pool_conn(conn)
```

Add startup/shutdown events:
```python
@app.on_event("startup")
def startup():
    init_pool()

@app.on_event("shutdown")
def shutdown():
    close_pool()
```

### 3. Refactor all endpoints

Every endpoint changes from:
```python
def some_endpoint(...):
    conn = get_conn()
    try:
        ...
    finally:
        conn.close()
```

To:
```python
def some_endpoint(..., conn=Depends(get_db)):
    ...
```

This eliminates:
- The connection leak (dependency always runs finally block)
- The repeated try/finally boilerplate (13 occurrences in api.py)
- The lack of pooling (connections reused from pool)

### Endpoints to refactor (all 11):
- `create_session_endpoint` (line 146)
- `get_session_endpoint` (line 195)
- `list_sessions_endpoint` (line 210)
- `delete_session_endpoint` (line 243)
- `restore_session_endpoint` (line 257)
- `permanently_delete_session_endpoint` (line 271)
- `rename_session_endpoint` (line 285)
- `rerun_session_endpoint` (line 299)
- `run_wtp_endpoint` (line 355)
- `export_csv_endpoint` (line 483)
- `export_pdf_endpoint` (line 503)

### 4. Keep `get_conn()` for non-API use
Scraper, CLI, and batch scripts still use `get_conn()` directly — that's fine for those contexts.

## Tests
- Update `test_api.py` to mock the `get_db` dependency instead of patching `get_conn`
- Test that connections are returned to pool even when endpoints raise
- Test pool initialization and shutdown

## Files Touched
- `src/focus_groups/db.py` (add pool functions)
- `src/focus_groups/api.py` (add dependency, refactor all endpoints)
- `tests/test_api.py` (update connection mocking)
