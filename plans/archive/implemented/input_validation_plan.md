# Fix: Bound Input Validation ✅ IMPLEMENTED

## Problem
- `num_personas` has no upper bound — attacker can set `num_personas=10000` to trigger 10,000 Claude API calls
- `question` has no max length — unbounded string passed to Claude
- ILIKE wildcards (`%`, `_`) in search parameter are not escaped
- No validation for zero/negative `num_personas`, empty question, or invalid sector values

## Severity: MEDIUM (input bounds) + HIGH (cost amplification via unbounded num_personas)

## Changes

### 1. Update Pydantic models in `api.py`

```python
from pydantic import BaseModel, Field, model_validator

class SessionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    num_personas: int = Field(ge=1, le=50)
    sector: Literal["tech", "financial", "political"] | None = None
    demographic_filter: dict | None = None

class RerunRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    sector: Literal["tech", "financial", "political"] | None = None
    num_personas: int | None = Field(default=None, ge=1, le=50)
    demographic_filter: dict | None = None
```

Key constraints:
- `num_personas`: 1–50 (50 serial Claude calls is already expensive)
- `question`: 1–2000 chars
- `sector`: enum of valid values instead of free-form string

### 2. Escape ILIKE wildcards in `sessions.py`

In `_build_filter_clause`, escape `%` and `_` in the search parameter:

```python
if search:
    escaped = search.replace("%", r"\%").replace("_", r"\_")
    conditions.append("question ILIKE %s ESCAPE '\\'")
    params.append(f"%{escaped}%")
```

### 3. Validate `segment_by` in `WtpRequest`

```python
class WtpRequest(BaseModel):
    segment_by: Literal[
        "age_group", "gender", "income_bracket",
        "education_level", "region"
    ] = "income_bracket"
```

## Tests
- `test_input_validation.py`:
  - `num_personas=0` → 422
  - `num_personas=-1` → 422
  - `num_personas=51` → 422
  - `question=""` → 422
  - `question` with 2001+ chars → 422
  - `sector="invalid"` → 422
  - Search with `%` and `_` characters works correctly (no wildcard injection)
  - Valid inputs pass through normally

## Files Touched
- `src/focus_groups/api.py` (update models)
- `src/focus_groups/sessions.py` (escape ILIKE)
- `tests/test_input_validation.py` (new)
