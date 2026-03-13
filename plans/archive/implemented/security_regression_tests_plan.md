# Fix: Add Security Regression Tests ✅ IMPLEMENTED

## Problem
- No SQL injection regression tests for the dynamic WHERE clause in `sessions.py`
- No CSV injection tests (formulas starting with `=`, `+`, `-`, `@` in exported data)
- No input validation boundary tests
- No Content-Disposition header injection tests
- No export security tests for special characters

## Severity: CRITICAL (SQL injection) + HIGH (CSV injection) + MEDIUM (others)

## Test Plan: `tests/test_security.py`

### SQL Injection Tests

Test `_build_filter_clause` and the endpoints that use it with malicious inputs:

```python
# Search parameter attacks
"'; DROP TABLE focus_group_sessions; --"
"' OR '1'='1"
"' UNION SELECT * FROM posts --"
"%' OR 1=1 --"
"'; DELETE FROM focus_group_sessions WHERE '1'='1"
```

Verify:
- Parameterized queries prevent execution (search returns 0 results, not an error)
- No SQL syntax errors (would indicate string interpolation)
- Tables remain intact after each test

### CSV Injection Tests

Test `export_csv()` with session data containing formula-injection payloads:

```python
# Payloads in question, persona_summary, response_text
"=cmd|'/C calc'!A0"
"+cmd|'/C calc'!A0"
"-cmd|'/C calc'!A0"
"@SUM(1+1)*cmd|'/C calc'!A0"
"=HYPERLINK(\"http://evil.com\",\"click\")"
```

Verify:
- Values are properly quoted by `csv.writer` (they will be, but prove it)
- Consider prefixing cells starting with `=+-@` with a single quote or tab

### Content-Disposition Header Injection

Test export endpoints with session IDs containing:
```python
"abc\r\nContent-Type: text/html"
"abc%0d%0aContent-Type: text/html"
```

Verify: Response headers are not split/injected. (FastAPI/Starlette should handle this, but verify.)

### Input Validation Boundary Tests

Test the Pydantic models at their boundaries:
- `num_personas=0`, `num_personas=1`, `num_personas=50`, `num_personas=51`
- `question` at exactly max length, 1 over max length
- Empty `question`
- `sector` with invalid value
- `demographic_filter` with deeply nested dicts
- `price_points` with negative numbers, zero, extremely large values

### Special Character Tests

Test with Unicode edge cases in question/response fields:
- Null bytes: `"test\x00value"`
- Unicode BOM: `"\ufeff"`
- RTL override: `"\u202e"`
- Very long strings (just under limit)

## Files Touched
- `tests/test_security.py` (new, ~250 lines)
- `src/focus_groups/export.py` (add CSV injection prefix if needed)
