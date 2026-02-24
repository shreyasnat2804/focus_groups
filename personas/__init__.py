"""
personas — public API for the persona selection library.
"""

from personas.cards import PersonaCard
from personas.selection import select_personas
from personas.mmr import mmr_select
from personas.diversity import avg_pairwise_distance
from personas.profiles import build_system_prompt, format_demographic_summary

__all__ = [
    "PersonaCard",
    "select_personas",
    "mmr_select",
    "avg_pairwise_distance",
    "build_system_prompt",
    "format_demographic_summary",
]
