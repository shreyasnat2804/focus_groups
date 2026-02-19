"""
Demographic tagger — two-layer inference pipeline.

Layer 1: Self-disclosure regex (confidence 0.85–0.95)
  Scans post text for explicit mentions of age, gender, parent status, income.

Layer 2: Subreddit priors (confidence 0.4–0.7)
  Applies community-level priors for dimensions not covered by Layer 1.

Returns:
    list[dict] — each dict has keys: dimension, value, confidence, method
"""

import re

# ---------------------------------------------------------------------------
# Age bucket mapping
# ---------------------------------------------------------------------------

def _age_to_bucket(age: int) -> str | None:
    if age < 13:
        return None  # too young, likely noise
    if age < 18:
        return "under_18"
    if age < 25:
        return "18-24"
    if age < 35:
        return "25-34"
    if age < 45:
        return "35-44"
    if age < 55:
        return "45-54"
    if age < 65:
        return "55-64"
    return "65+"


# ---------------------------------------------------------------------------
# Layer 1 — Self-disclosure regex patterns
# ---------------------------------------------------------------------------

# Age patterns — capture integer age
_AGE_PATTERNS = [
    # "I'm 28 years old", "I am 34 years old"
    re.compile(r"\bi(?:'m| am)\s+(\d{1,3})\s+years?\s+old\b", re.IGNORECASE),
    # "as a 25-year-old", "as a 30 year old"
    re.compile(r"\bas\s+a[n]?\s+(\d{1,3})[\s-]years?[\s-]old\b", re.IGNORECASE),
    # "25yo", "34yo", "25 yo"
    re.compile(r"\b(\d{1,3})\s*yo\b", re.IGNORECASE),
    # "28y/o", "34 y/o"
    re.compile(r"\b(\d{1,3})\s*y/o\b", re.IGNORECASE),
    # "34F", "28M", "45NB" at word boundary or in parens
    re.compile(r"(?:^|[\s(,])(\d{1,3})[FfMmNn][Bb]?\b"),
    # "age 28", "age: 28"
    re.compile(r"\bage[:\s]+(\d{1,3})\b", re.IGNORECASE),
    # "I'm in my late 20s" — skip (too vague for precise bucket)
    # "turned 30", "just turned 45"
    re.compile(r"\b(?:just\s+)?turned\s+(\d{1,3})\b", re.IGNORECASE),
]

# Gender patterns — (pattern, value)
_GENDER_PATTERNS = [
    (re.compile(r"(?:^|[\s(,])\d{1,3}[Ff]\b"), "female"),
    (re.compile(r"(?:^|[\s(,])\d{1,3}[Mm]\b"), "male"),
    (re.compile(r"\bi\s+am\s+a\s+(?:woman|girl|lady|female)\b", re.IGNORECASE), "female"),
    (re.compile(r"\bi'?m\s+a\s+(?:woman|girl|lady|female)\b", re.IGNORECASE), "female"),
    (re.compile(r"\bi\s+am\s+a\s+(?:man|guy|male)\b", re.IGNORECASE), "male"),
    (re.compile(r"\bi'?m\s+a\s+(?:man|guy|male)\b", re.IGNORECASE), "male"),
    (re.compile(r"\bas\s+a\s+(?:woman|female)\b", re.IGNORECASE), "female"),
    (re.compile(r"\bas\s+a\s+(?:man|male|guy)\b", re.IGNORECASE), "male"),
    (re.compile(r"\bmy\s+(?:husband|boyfriend|fiance|fiancé)\b", re.IGNORECASE), "female"),
    (re.compile(r"\bmy\s+(?:wife|girlfriend|fiancee|fiancée)\b", re.IGNORECASE), "male"),
    (re.compile(r"\bi\s+identify\s+as\s+(?:a\s+)?(?:woman|female)\b", re.IGNORECASE), "female"),
    (re.compile(r"\bi\s+identify\s+as\s+(?:a\s+)?(?:man|male)\b", re.IGNORECASE), "male"),
    (re.compile(r"\b(?:she/her|she\/her)\b", re.IGNORECASE), "female"),
    (re.compile(r"\b(?:he/him|he\/him)\b", re.IGNORECASE), "male"),
]

# Parent status patterns
_PARENT_PATTERNS = [
    (re.compile(r"\bmy\s+(?:kid|kids|children|child|son|daughter|toddler|baby|infant)\b", re.IGNORECASE), "parent"),
    (re.compile(r"\bas\s+a\s+(?:mom|dad|mother|father|parent)\b", re.IGNORECASE), "parent"),
    (re.compile(r"\bi'?m\s+a\s+(?:mom|dad|mother|father|parent)\b", re.IGNORECASE), "parent"),
    (re.compile(r"\bi\s+am\s+a\s+(?:mom|dad|mother|father|parent)\b", re.IGNORECASE), "parent"),
    (re.compile(r"\b(?:my\s+)?(?:newborn|toddler)\b", re.IGNORECASE), "parent"),
    (re.compile(r"\bexpecting\s+(?:a|our)\s+(?:baby|child|kid)\b", re.IGNORECASE), "parent"),
    (re.compile(r"\bno\s+kids?\b", re.IGNORECASE), "non_parent"),
    (re.compile(r"\bchildfree\b", re.IGNORECASE), "non_parent"),
    (re.compile(r"\bchild\s*less\b", re.IGNORECASE), "non_parent"),
    (re.compile(r"\bdon'?t\s+have\s+(?:any\s+)?kids?\b", re.IGNORECASE), "non_parent"),
]

# Income patterns — numeric amount parsers
# Simple: match "$120k", "$200K", "$35k" anywhere (no \b before $ needed)
_INCOME_PATTERN_K = re.compile(r"\$([\d]+)[kK]\b")
# Large raw dollar amounts (>= 5 chars so we don't match "$50" for a single purchase)
_INCOME_PATTERN_DOLLAR = re.compile(r"\$([\d,]{5,})\b")

# Narrative income signals: (pattern, bracket_value)
_INCOME_NARRATIVE_PATTERNS = [
    (re.compile(r"\bsix[\s-]figures?\b", re.IGNORECASE), "high_income"),
    (re.compile(r"\bseven[\s-]figures?\b", re.IGNORECASE), "high_income"),
    (re.compile(r"\bminimum\s+wage\b", re.IGNORECASE), "lower_income"),
    (re.compile(r"\bliving\s+paycheck\s+to\s+paycheck\b", re.IGNORECASE), "lower_income"),
    (re.compile(r"\bcan'?t\s+afford\b", re.IGNORECASE), "lower_income"),
    (re.compile(r"\bstruggling\s+financially\b", re.IGNORECASE), "lower_income"),
    (re.compile(r"\bfinancially\s+struggling\b", re.IGNORECASE), "lower_income"),
]


def _income_from_dollar_amount(amount: int) -> str:
    """Map annual dollar amount to income bracket."""
    if amount < 30000:
        return "lower_income"
    if amount < 75000:
        return "middle_income"
    if amount < 150000:
        return "high_income"
    return "high_income"


def _income_from_k(k_value: int) -> str:
    """Map $Xk to income bracket (assumes annual)."""
    return _income_from_dollar_amount(k_value * 1000)


def _extract_age_tags(text: str) -> list[dict]:
    tags = []
    for pattern in _AGE_PATTERNS:
        m = pattern.search(text)
        if m:
            try:
                age = int(m.group(1))
            except (IndexError, ValueError):
                continue
            bucket = _age_to_bucket(age)
            if bucket:
                tags.append({
                    "dimension": "age_group",
                    "value": bucket,
                    "confidence": 0.90,
                    "method": "self_disclosure",
                })
                break  # take first match only
    return tags


def _extract_gender_tags(text: str) -> list[dict]:
    for pattern, value in _GENDER_PATTERNS:
        if pattern.search(text):
            return [{
                "dimension": "gender",
                "value": value,
                "confidence": 0.85,
                "method": "self_disclosure",
            }]
    return []


def _extract_parent_tags(text: str) -> list[dict]:
    for pattern, value in _PARENT_PATTERNS:
        if pattern.search(text):
            return [{
                "dimension": "parent_status",
                "value": value,
                "confidence": 0.85,
                "method": "self_disclosure",
            }]
    return []


def _extract_income_tags(text: str) -> list[dict]:
    # Narrative patterns first (no amount parsing needed)
    for pattern, value in _INCOME_NARRATIVE_PATTERNS:
        if pattern.search(text):
            return [{
                "dimension": "income_bracket",
                "value": value,
                "confidence": 0.85,
                "method": "self_disclosure",
            }]

    # Try $Xk / $XK pattern
    m = _INCOME_PATTERN_K.search(text)
    if m:
        try:
            k_val = int(m.group(1))
            # Plausible annual salary range: $15k–$5000k
            if 15 <= k_val <= 5000:
                return [{
                    "dimension": "income_bracket",
                    "value": _income_from_k(k_val),
                    "confidence": 0.88,
                    "method": "self_disclosure",
                }]
        except ValueError:
            pass

    # Try $XX,XXX or $XXXXX raw dollar amount (5+ chars → >= $10,000)
    for m in _INCOME_PATTERN_DOLLAR.finditer(text):
        try:
            amount = int(m.group(1).replace(",", ""))
            if amount >= 20000:  # likely annual income
                return [{
                    "dimension": "income_bracket",
                    "value": _income_from_dollar_amount(amount),
                    "confidence": 0.80,
                    "method": "self_disclosure",
                }]
        except ValueError:
            continue

    return []


# ---------------------------------------------------------------------------
# Layer 2 — Subreddit priors
# ---------------------------------------------------------------------------

SUBREDDIT_PRIORS: dict[str, dict[str, tuple[str, float]]] = {
    # Financial
    "povertyfinance":        {"income_bracket": ("lower_income", 0.6)},
    "fatFIRE":               {"income_bracket": ("high_income", 0.7)},
    "personalfinance":       {"income_bracket": ("middle_income", 0.4)},
    "financialindependence": {"income_bracket": ("middle_income", 0.5)},
    "wallstreetbets":        {"income_bracket": ("middle_income", 0.4)},
    "Bogleheads":            {"income_bracket": ("high_income", 0.5)},
    "investing":             {"income_bracket": ("middle_income", 0.4)},
    "Frugal":                {"income_bracket": ("middle_income", 0.4)},
    # Tech
    "cscareerquestions":     {"income_bracket": ("middle_income", 0.5), "age_group": ("25-34", 0.4)},
    "programming":           {"income_bracket": ("middle_income", 0.4), "age_group": ("25-34", 0.4)},
    "homelab":               {"income_bracket": ("middle_income", 0.4), "gender": ("male", 0.5)},
    "buildapc":              {"income_bracket": ("middle_income", 0.4), "gender": ("male", 0.5)},
    "techsupport":           {"age_group": ("25-34", 0.4)},
    "apple":                 {"income_bracket": ("middle_income", 0.4)},
    "Android":               {"income_bracket": ("middle_income", 0.4)},
    "AskTechnology":         {"age_group": ("25-34", 0.4)},
    # Political
    "NeutralPolitics":       {"age_group": ("25-34", 0.4)},
    "moderatepolitics":      {"age_group": ("25-34", 0.4)},
    "AskTrumpsupporters":    {"age_group": ("35-44", 0.4)},
    "Ask_Politics":          {"age_group": ("25-34", 0.4)},
    "PoliticalDiscussion":   {"age_group": ("25-34", 0.4)},
    "conservative":          {"age_group": ("35-44", 0.4)},
    "Libertarian":           {"age_group": ("25-34", 0.4)},
    "centrist":              {"age_group": ("25-34", 0.4)},
    # Age-specific
    "teenagers":             {"age_group": ("under_18", 0.7)},
    # Gender-specific
    "TwoXChromosomes":       {"gender": ("female", 0.6)},
    "AskMen":                {"gender": ("male", 0.6)},
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_DELETED_TEXTS = {"[deleted]", "[removed]"}


def tag_post(text: str, subreddit: str) -> list[dict]:
    """
    Run Layer 1 + Layer 2 tagging on a post.

    Layer 1 (self-disclosure regex) always takes priority.
    Layer 2 (subreddit priors) fills in uncovered dimensions only.

    Args:
        text: Combined title + selftext of the post.
        subreddit: Subreddit name (case-sensitive, as stored).

    Returns:
        List of tag dicts: {dimension, value, confidence, method}
    """
    text = (text or "").strip()
    if not text or text in _DELETED_TEXTS:
        return []

    tags: list[dict] = []
    covered: set[str] = set()

    # Layer 1
    for extractor in (
        _extract_age_tags,
        _extract_gender_tags,
        _extract_parent_tags,
        _extract_income_tags,
    ):
        found = extractor(text)
        for tag in found:
            if tag["dimension"] not in covered:
                tags.append(tag)
                covered.add(tag["dimension"])

    # Layer 2 — only for dimensions not already covered
    priors = SUBREDDIT_PRIORS.get(subreddit, {})
    for dimension, (value, confidence) in priors.items():
        if dimension not in covered:
            tags.append({
                "dimension": dimension,
                "value": value,
                "confidence": confidence,
                "method": "subreddit_prior",
            })
            covered.add(dimension)

    return tags
