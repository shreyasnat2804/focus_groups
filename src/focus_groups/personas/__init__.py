"""
personas — public API for the persona selection library.
"""

from focus_groups.personas.cards import PersonaCard
from focus_groups.personas.selection import select_personas
from focus_groups.personas.mmr import mmr_select
from focus_groups.personas.diversity import avg_pairwise_distance
from focus_groups.personas.profiles import build_system_prompt, format_demographic_summary

__all__ = [
    "PersonaCard",
    "select_personas",
    "mmr_select",
    "avg_pairwise_distance",
    "build_system_prompt",
    "format_demographic_summary",
]
