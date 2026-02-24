"""
DEPRECATED: src/persona.py has been replaced by the `personas` package.

Import from `personas` instead:

    from personas import PersonaCard, select_personas, mmr_select
    from personas.mmr import _cosine_similarity
"""

import warnings

warnings.warn(
    "src.persona is deprecated. Use the `personas` package instead: "
    "from personas import PersonaCard, select_personas, mmr_select",
    DeprecationWarning,
    stacklevel=2,
)

from personas.cards import PersonaCard
from personas.mmr import mmr_select, _cosine_similarity
from personas.selection import select_personas

__all__ = ["PersonaCard", "mmr_select", "_cosine_similarity", "select_personas"]
