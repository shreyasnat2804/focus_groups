# Fix: Export Security Hardening

## Problem
- CSV export doesn't protect against formula injection
- Content-Disposition header uses unsanitized session_id
- No CSP headers on any response
- `matplotlib` used in visualization but missing from `pyproject.toml`

## Severity: MEDIUM

## Changes

### 1. CSV Formula Injection Protection (`export.py`)

Prefix cell values starting with `=`, `+`, `-`, `@`, `\t`, `\r` with a single quote to prevent spreadsheet formula execution:

```python
def _sanitize_csv_value(val: str) -> str:
    """Prefix formula-triggering characters to prevent CSV injection."""
    if val and val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val}"
    return val
```

Apply to `persona_summary` and `response_text` fields in `export_csv()`.

### 2. Sanitize Content-Disposition header (`api.py`)

Session IDs are UUIDs from Postgres so injection is unlikely, but add a safeguard:

```python
import re

def _safe_filename(name: str) -> str:
    """Remove any characters that could cause header injection."""
    return re.sub(r'[^a-zA-Z0-9_-]', '', name)
```

Use in export endpoints:
```python
safe_id = _safe_filename(session_id)
headers={"Content-Disposition": f'attachment; filename="session_{safe_id}.csv"'}
```

### 3. Add `matplotlib` to `pyproject.toml`

```toml
"matplotlib>=3.8",
```

Currently imported in `wtp/visualization.py` but not declared as a dependency.

## Tests
- Covered by `test_security.py` (CSV injection and Content-Disposition tests)
- Add a test that `_sanitize_csv_value` prefixes dangerous values

## Files Touched
- `src/focus_groups/export.py` (add sanitization)
- `src/focus_groups/api.py` (sanitize Content-Disposition)
- `pyproject.toml` (add matplotlib)
