# TAGGING.md — Three-Layer Demographic Inference

## Overview

Demographic inference runs in 3 layers, each filling gaps left by the previous:

1. **Self-disclosure detection** (highest confidence, lowest coverage)
2. **Subreddit community priors** (medium confidence, high coverage)
3. **NLP classifier** (trained on PANDORA dataset, gap-filling)

Each layer produces `(dimension, value, confidence, method)` tuples stored in `demographic_tags`.

## Layer 1: Self-Disclosure Detection

Regex patterns applied to post text and author bios. High confidence (0.85-0.95) when matched.

### Patterns

```python
import re

SELF_DISCLOSURE_PATTERNS = {
    "age_group": [
        (r"\b(?:i'?m|i am|being)\s+(\d{2})\s*(?:yo|y/?o|years?\s*old)", "extract_age_group"),
        (r"\b(\d{2})\s*[MFmf]\b", "extract_age_group"),           # "34F", "28M"
        (r"\bas a (\d{2})\s*(?:year|yr)", "extract_age_group"),
    ],
    "gender": [
        (r"\b(\d{2})\s*([MFmf])\b", "extract_gender_from_age"),   # "34F" → female
        (r"\bas a (?:wo)?man\b", "direct_gender"),
        (r"\b(?:i'?m|i am) (?:a )?(male|female|man|woman)\b", "direct_gender"),
    ],
    "parent_status": [
        (r"\bmy (?:kid|child|son|daughter|baby|toddler)", "is_parent"),
        (r"\bas a (?:mom|dad|parent|mother|father)\b", "is_parent"),
    ],
}

def extract_age_group(age: int) -> str:
    if age < 18: return "under_18"
    if age < 25: return "18-24"
    if age < 35: return "25-34"
    if age < 45: return "35-44"
    if age < 55: return "45-54"
    return "55+"
```

### Confidence: 0.90 for explicit patterns, 0.85 for ambiguous matches.

## Layer 2: Subreddit Community Priors

Assign demographic distributions based on known subreddit demographics. Lower confidence (0.4-0.6) — these are population-level priors, not individual-level.

```python
SUBREDDIT_PRIORS = {
    "povertyfinance":   {"income_bracket": ("lower_income", 0.6)},
    "fatFIRE":          {"income_bracket": ("high_income", 0.7)},
    "personalfinance":  {"income_bracket": ("middle_income", 0.4)},
    "teenagers":        {"age_group": ("under_18", 0.7)},
    "retirement":       {"age_group": ("55+", 0.5)},
    "TwoXChromosomes":  {"gender": ("female", 0.6)},
    "AskMen":           {"gender": ("male", 0.6)},
    # ... extend as needed
}
```

**Key decision**: Subreddit priors only apply when Layer 1 found no match for that dimension. They're weak signals — never override a self-disclosure.

## Layer 3: NLP Classifier (PANDORA Dataset)

### PANDORA Dataset

- Source: https://psy.takelab.fer.hr/datasets/all/pandora/
- Contains Reddit posts with author personality traits and demographics
- ~10k users with age, gender, location, income proxies
- Use this as training data for a text classifier

### Classifier Architecture

```python
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# Multi-label classifier: predict age_group, gender, income_bracket from text
# Fine-tune on PANDORA → apply to unlabeled posts
model_name = "distilbert-base-uncased"
num_labels_per_dim = {"age_group": 6, "gender": 3, "income_bracket": 4}
```

### Training

```bash
python3 src/train_tagger.py \
    --dataset pandora \
    --model distilbert-base-uncased \
    --epochs 5 \
    --batch-size 32 \
    --output models/demographic_classifier/
```

### Confidence Calibration

- Raw softmax outputs are poorly calibrated. Apply temperature scaling on a held-out set.
- Only tag when confidence > 0.5 for any single class.
- Confidence for NLP predictions: 0.5-0.75 range.

## Merging Strategy

For each post, for each demographic dimension:
1. If Layer 1 matched → use it (highest confidence)
2. Else if Layer 2 has a prior for the subreddit → use it
3. Else if Layer 3 classifier has confidence > 0.5 → use it
4. Else → no tag for that dimension (leave gaps, don't guess)

Multiple tags per post are normal (e.g., age from self-disclosure + income from subreddit prior).

## Pitfalls

- **Don't overfit on self-disclosure**: Only ~5-10% of posts contain explicit demographics. The system must work with sparse labels.
- **Subreddit priors are stereotypes**: They're useful as population-level signals but will be wrong for many individuals. Keep confidence low.
- **PANDORA is small**: ~10k users. The NLP classifier will be noisy. That's acceptable — we need broad coverage, not perfection.
- **Age from "34F" format**: Common in advice subreddits (AITA, relationships). Very reliable when present.
- **Sarcasm/roleplay**: "As a 90-year-old grandma..." in r/teenagers is not a real self-disclosure. Consider subreddit context.
