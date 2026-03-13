"""
PersonaCard dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PersonaCard:
    post_id: int
    demographic_tags: dict  # {dimension: value}
    text_excerpt: str       # first N chars of post text (truncation done by caller)
    sector: str | None

    def __repr__(self) -> str:
        tags = ", ".join(f"{k}={v}" for k, v in self.demographic_tags.items())
        excerpt = self.text_excerpt[:120].replace("\n", " ")
        return f"PersonaCard(id={self.post_id}, sector={self.sector}, [{tags}], \"{excerpt}...\")"
