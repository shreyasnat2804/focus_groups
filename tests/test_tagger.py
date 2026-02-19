"""
Unit tests for src/tagger.py — no DB required.
Run with: python3 -m pytest tests/test_tagger.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tagger import tag_post


def _get(tags: list[dict], dimension: str) -> dict | None:
    """Return first tag matching dimension, or None."""
    return next((t for t in tags if t["dimension"] == dimension), None)


# ---------------------------------------------------------------------------
# Age extraction
# ---------------------------------------------------------------------------

def test_age_extraction_years_old():
    tags = tag_post("I'm 28 years old and looking for advice.", "personalfinance")
    age_tag = _get(tags, "age_group")
    assert age_tag is not None
    assert age_tag["value"] == "25-34"
    assert age_tag["method"] == "self_disclosure"


def test_age_extraction_yo():
    tags = tag_post("As a 22yo I have trouble saving.", "personalfinance")
    age_tag = _get(tags, "age_group")
    assert age_tag is not None
    assert age_tag["value"] == "18-24"
    assert age_tag["method"] == "self_disclosure"


def test_age_extraction_turned():
    tags = tag_post("I just turned 45 last month.", "personalfinance")
    age_tag = _get(tags, "age_group")
    assert age_tag is not None
    assert age_tag["value"] == "45-54"


def test_age_under_18():
    tags = tag_post("I'm 16 years old and want to start investing.", "personalfinance")
    age_tag = _get(tags, "age_group")
    assert age_tag is not None
    assert age_tag["value"] == "under_18"


def test_age_65_plus():
    tags = tag_post("I am 70 years old, retired.", "personalfinance")
    age_tag = _get(tags, "age_group")
    assert age_tag is not None
    assert age_tag["value"] == "65+"


# ---------------------------------------------------------------------------
# Age + gender from "NNF" / "NNM" suffix format
# ---------------------------------------------------------------------------

def test_age_suffix_format_female():
    tags = tag_post("34F here, recently got a promotion.", "personalfinance")
    age_tag = _get(tags, "age_group")
    gender_tag = _get(tags, "gender")
    assert age_tag is not None
    assert age_tag["value"] == "25-34"  # 34 < 35, so 25-34 bucket
    assert gender_tag is not None
    assert gender_tag["value"] == "female"
    assert gender_tag["method"] == "self_disclosure"


def test_age_suffix_format_male():
    tags = tag_post("28M, just started my first job.", "cscareerquestions")
    age_tag = _get(tags, "age_group")
    gender_tag = _get(tags, "gender")
    assert age_tag is not None
    assert age_tag["value"] == "25-34"
    assert gender_tag is not None
    assert gender_tag["value"] == "male"


# ---------------------------------------------------------------------------
# Gender direct disclosure
# ---------------------------------------------------------------------------

def test_gender_direct_female():
    tags = tag_post("I am a woman working in tech.", "cscareerquestions")
    gender_tag = _get(tags, "gender")
    assert gender_tag is not None
    assert gender_tag["value"] == "female"
    assert gender_tag["method"] == "self_disclosure"


def test_gender_direct_male():
    tags = tag_post("I'm a man trying to understand my finances.", "personalfinance")
    gender_tag = _get(tags, "gender")
    assert gender_tag is not None
    assert gender_tag["value"] == "male"
    assert gender_tag["method"] == "self_disclosure"


def test_gender_husband_implies_female():
    tags = tag_post("My husband and I are buying a house.", "personalfinance")
    gender_tag = _get(tags, "gender")
    assert gender_tag is not None
    assert gender_tag["value"] == "female"


def test_gender_pronouns_she_her():
    tags = tag_post("she/her — asking about salary negotiation", "cscareerquestions")
    gender_tag = _get(tags, "gender")
    assert gender_tag is not None
    assert gender_tag["value"] == "female"


# ---------------------------------------------------------------------------
# Parent status
# ---------------------------------------------------------------------------

def test_parent_status_kid():
    tags = tag_post("My kid is 5 and I'm worried about college savings.", "personalfinance")
    parent_tag = _get(tags, "parent_status")
    assert parent_tag is not None
    assert parent_tag["value"] == "parent"
    assert parent_tag["method"] == "self_disclosure"


def test_parent_status_as_a_mom():
    tags = tag_post("As a mom of two, budgeting is hard.", "personalfinance")
    parent_tag = _get(tags, "parent_status")
    assert parent_tag is not None
    assert parent_tag["value"] == "parent"


def test_parent_status_non_parent():
    tags = tag_post("No kids, so I have more disposable income.", "personalfinance")
    parent_tag = _get(tags, "parent_status")
    assert parent_tag is not None
    assert parent_tag["value"] == "non_parent"


def test_parent_status_childfree():
    tags = tag_post("I'm childfree by choice.", "personalfinance")
    parent_tag = _get(tags, "parent_status")
    assert parent_tag is not None
    assert parent_tag["value"] == "non_parent"


# ---------------------------------------------------------------------------
# Income disclosure
# ---------------------------------------------------------------------------

def test_income_disclosure_k():
    tags = tag_post("I earn $120k and still feel broke.", "personalfinance")
    income_tag = _get(tags, "income_bracket")
    assert income_tag is not None
    assert income_tag["value"] == "high_income"
    assert income_tag["method"] == "self_disclosure"


def test_income_disclosure_low():
    tags = tag_post("I make $35k and can barely pay rent.", "povertyfinance")
    income_tag = _get(tags, "income_bracket")
    assert income_tag is not None
    assert income_tag["value"] == "middle_income"  # 35k maps to middle
    assert income_tag["method"] == "self_disclosure"


def test_income_six_figures():
    tags = tag_post("I make six figures as a software engineer.", "cscareerquestions")
    income_tag = _get(tags, "income_bracket")
    assert income_tag is not None
    assert income_tag["value"] == "high_income"
    assert income_tag["method"] == "self_disclosure"


def test_income_minimum_wage():
    tags = tag_post("Working minimum wage, can't save anything.", "povertyfinance")
    income_tag = _get(tags, "income_bracket")
    assert income_tag is not None
    assert income_tag["value"] == "lower_income"
    assert income_tag["method"] == "self_disclosure"


def test_income_paycheck_to_paycheck():
    tags = tag_post("Living paycheck to paycheck is exhausting.", "povertyfinance")
    income_tag = _get(tags, "income_bracket")
    assert income_tag is not None
    assert income_tag["value"] == "lower_income"


# ---------------------------------------------------------------------------
# Subreddit priors (Layer 2)
# ---------------------------------------------------------------------------

def test_subreddit_prior_poverty():
    # Empty text → only subreddit prior applies
    tags = tag_post("What's everyone's take?", "povertyfinance")
    income_tag = _get(tags, "income_bracket")
    assert income_tag is not None
    assert income_tag["value"] == "lower_income"
    assert income_tag["method"] == "subreddit_prior"
    assert income_tag["confidence"] == 0.6


def test_subreddit_prior_fatfire():
    tags = tag_post("Looking for investment advice.", "fatFIRE")
    income_tag = _get(tags, "income_bracket")
    assert income_tag is not None
    assert income_tag["value"] == "high_income"
    assert income_tag["method"] == "subreddit_prior"


def test_subreddit_prior_teenagers():
    tags = tag_post("First job question.", "teenagers")
    age_tag = _get(tags, "age_group")
    assert age_tag is not None
    assert age_tag["value"] == "under_18"
    assert age_tag["method"] == "subreddit_prior"


def test_subreddit_prior_twox():
    tags = tag_post("Need advice on this situation.", "TwoXChromosomes")
    gender_tag = _get(tags, "gender")
    assert gender_tag is not None
    assert gender_tag["value"] == "female"
    assert gender_tag["method"] == "subreddit_prior"


# ---------------------------------------------------------------------------
# Layer 1 overrides Layer 2
# ---------------------------------------------------------------------------

def test_layer1_overrides_layer2_income():
    """Self-disclosed $200k should override povertyfinance prior of lower_income."""
    tags = tag_post("I make $200k but grew up poor and still use this sub.", "povertyfinance")
    income_tags = [t for t in tags if t["dimension"] == "income_bracket"]
    # There must be exactly one income tag and it must be from self_disclosure
    assert len(income_tags) == 1
    assert income_tags[0]["method"] == "self_disclosure"
    assert income_tags[0]["value"] == "high_income"


def test_layer1_overrides_layer2_age():
    """Self-disclosed age should override subreddit prior."""
    tags = tag_post("I'm 45 years old lurking here.", "teenagers")
    age_tags = [t for t in tags if t["dimension"] == "age_group"]
    assert len(age_tags) == 1
    assert age_tags[0]["method"] == "self_disclosure"
    assert age_tags[0]["value"] == "45-54"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_deleted_text():
    tags = tag_post("[deleted]", "personalfinance")
    assert tags == []


def test_removed_text():
    tags = tag_post("[removed]", "personalfinance")
    assert tags == []


def test_empty_text():
    tags = tag_post("", "personalfinance")
    assert tags == []


def test_whitespace_only():
    tags = tag_post("   ", "personalfinance")
    assert tags == []


def test_no_disclosure_no_prior():
    """Generic subreddit with no priors and no disclosures → no tags."""
    tags = tag_post("Interesting post about stuff.", "MildlyInteresting")
    assert tags == []


def test_multiple_dimensions():
    """28F, parent → age + gender + parent all tagged from Layer 1."""
    tags = tag_post("28F here. My kid just started school.", "personalfinance")
    age_tag = _get(tags, "age_group")
    gender_tag = _get(tags, "gender")
    parent_tag = _get(tags, "parent_status")
    assert age_tag is not None and age_tag["value"] == "25-34"
    assert gender_tag is not None and gender_tag["value"] == "female"
    assert parent_tag is not None and parent_tag["value"] == "parent"
    # All from self_disclosure
    for tag in [age_tag, gender_tag, parent_tag]:
        assert tag["method"] == "self_disclosure"


def test_age_y_o_format():
    tags = tag_post("34 y/o asking for help.", "personalfinance")
    age_tag = _get(tags, "age_group")
    assert age_tag is not None
    assert age_tag["value"] == "25-34"  # 34 < 35, so 25-34 bucket


def test_unknown_subreddit_no_prior():
    tags = tag_post("Generic post text.", "SomeRandomSub")
    assert tags == []


def test_confidence_layer1_higher_than_layer2():
    """Layer 1 confidence (≥0.85) must be higher than Layer 2 (≤0.7)."""
    l1_tags = tag_post("I'm 28 years old.", "personalfinance")
    l2_tags = tag_post("Generic post.", "povertyfinance")
    for t in l1_tags:
        if t["method"] == "self_disclosure":
            assert t["confidence"] >= 0.85
    for t in l2_tags:
        if t["method"] == "subreddit_prior":
            assert t["confidence"] <= 0.7
