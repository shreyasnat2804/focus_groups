"""
Tests for the prompts directory and prompt loading.

What we expect:
- All expected prompt template files exist in the prompts directory
- Each template file is non-empty
- Templates with placeholders can be formatted with expected variables
- build_system_prompt still produces correct output after refactor to file-based prompts
- load_prompt_template returns the raw template string for a given filename
- load_prompt_template raises FileNotFoundError for missing templates
"""

import pytest
from pathlib import Path

from focus_groups.personas.cards import PersonaCard
from focus_groups.personas.profiles import build_system_prompt, load_prompt_template

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "src" / "focus_groups" / "prompts"

EXPECTED_FILES = ["identity.txt", "voice.txt", "instructions.txt", "format.txt"]


# --- Prompt files exist and are non-empty ---

@pytest.mark.parametrize("filename", EXPECTED_FILES)
def test_prompt_file_exists(filename):
    path = PROMPTS_DIR / filename
    assert path.exists(), f"Missing prompt file: {filename}"


@pytest.mark.parametrize("filename", EXPECTED_FILES)
def test_prompt_file_nonempty(filename):
    path = PROMPTS_DIR / filename
    content = path.read_text()
    assert len(content.strip()) > 0, f"Prompt file is empty: {filename}"


# --- load_prompt_template ---

def test_load_prompt_template_returns_string():
    result = load_prompt_template("identity.txt")
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_load_prompt_template_missing_file():
    with pytest.raises(FileNotFoundError):
        load_prompt_template("nonexistent.txt")


# --- build_system_prompt with file-based templates ---

def make_card(**kwargs) -> PersonaCard:
    defaults = dict(
        post_id=1,
        demographic_tags={"age_group": "25-34", "gender": "male"},
        text_excerpt="I think the tech industry is moving too fast.",
        sector="tech",
    )
    defaults.update(kwargs)
    return PersonaCard(**defaults)


def test_build_prompt_contains_demographics():
    card = make_card(demographic_tags={"age_group": "25-34", "gender": "male"})
    result = build_system_prompt(card)
    assert "25-34" in result
    assert "male" in result


def test_build_prompt_contains_excerpt():
    card = make_card(text_excerpt="I love discussing politics online.")
    result = build_system_prompt(card)
    assert "I love discussing politics online." in result


def test_build_prompt_contains_sector():
    card = make_card(sector="financial")
    result = build_system_prompt(card)
    assert "financial" in result


def test_build_prompt_sector_none():
    card = make_card(sector=None)
    result = build_system_prompt(card)
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_prompt_empty_tags():
    card = make_card(demographic_tags={})
    result = build_system_prompt(card)
    assert "unspecified" in result.lower() or "Demographics" in result


def test_build_prompt_contains_sentiment_instruction():
    card = make_card()
    result = build_system_prompt(card)
    assert "POSITIVE" in result
    assert "NEGATIVE" in result


def test_build_prompt_instructs_honest_reaction():
    card = make_card()
    result = build_system_prompt(card)
    lower = result.lower()
    assert "honest" in lower or "react" in lower or "opinion" in lower
