import json
import re
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config" / "subreddits.json"

# Load subreddit → demographic mapping
def load_subreddit_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


SUBREDDIT_CONFIG = None


def get_subreddit_config():
    global SUBREDDIT_CONFIG
    if SUBREDDIT_CONFIG is None:
        SUBREDDIT_CONFIG = load_subreddit_config()
    return SUBREDDIT_CONFIG


AGE_PATTERNS = [
    (r"\b(\d{1,2})\s*[/]?\s*[mfMF]\b", None),  # "24M", "30/F"
    (r"\bI'?m\s+(\d{2})\b", None),  # "I'm 24"
    (r"\b(\d{2})\s*year[s]?\s*old\b", None),  # "24 years old"
]

GENDER_PATTERNS = [
    (r"\b\d{1,2}\s*[/]?\s*[mM]\b", "M"),
    (r"\b\d{1,2}\s*[/]?\s*[fF]\b", "F"),
    (r"\b(?:I'?m a|as a)\s+(?:guy|man|male|dude)\b", "M"),
    (r"\b(?:I'?m a|as a)\s+(?:girl|woman|female|lady)\b", "F"),
]


def age_to_group(age):
    if age < 18:
        return None
    if age <= 24:
        return "18-24"
    if age <= 34:
        return "25-34"
    if age <= 54:
        return "35-54"
    return "55+"


def extract_from_text(text):
    """Extract demographic signals from post text. Returns partial tags dict."""
    tags = {}

    # Age extraction
    for pattern, _ in AGE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            try:
                age = int(m.group(1))
                group = age_to_group(age)
                if group:
                    tags["age_group"] = group
                    break
            except (ValueError, IndexError):
                pass

    # Gender extraction
    for pattern, gender in GENDER_PATTERNS:
        if re.search(pattern, text):
            tags["gender"] = gender
            break

    return tags


def tag_post(text, subreddit):
    """Produce demographic tags for a post. Combines subreddit-based and text-based signals."""
    config = get_subreddit_config()
    sub_config = config.get(subreddit, {})
    sub_tags = sub_config.get("demographic_tags", {})

    # Start with subreddit-level tags
    tags = {
        "age_group": sub_tags.get("age_group", "unknown"),
        "gender": sub_tags.get("gender", "unknown"),
        "income_proxy": sub_tags.get("income_proxy", "unknown"),
    }

    # Text-based extraction can override "unknown" fields
    text_tags = extract_from_text(text)
    confidence = 0.5  # base confidence from subreddit mapping

    for key, val in text_tags.items():
        if tags.get(key) == "unknown":
            tags[key] = val
            confidence += 0.1
        elif tags.get(key) == val:
            confidence += 0.15  # corroborating signal

    # Higher confidence if subreddit has explicit demographic tags
    known_count = sum(1 for v in tags.values() if v != "unknown")
    confidence = min(confidence + known_count * 0.05, 1.0)

    tags["confidence"] = round(confidence, 2)
    return tags
