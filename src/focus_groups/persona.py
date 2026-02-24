"""
DEPRECATED: focus_groups.persona has been replaced by focus_groups.personas.

Import from focus_groups.personas instead:

    from focus_groups.personas import PersonaCard, select_personas, mmr_select
    from focus_groups.personas.mmr import _cosine_similarity
"""

import warnings

warnings.warn(
    "focus_groups.persona is deprecated. Use focus_groups.personas instead: "
    "from focus_groups.personas import PersonaCard, select_personas, mmr_select",
    DeprecationWarning,
    stacklevel=2,
)

from focus_groups.personas.cards import PersonaCard
from focus_groups.personas.mmr import mmr_select, _cosine_similarity
from focus_groups.personas.selection import select_personas

__all__ = ["PersonaCard", "mmr_select", "_cosine_similarity", "select_personas"]
