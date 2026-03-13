"""
Demographic segmentation for WTP analysis results.

Groups Van Westendorp and Gabor-Granger responses by demographic
dimensions (e.g. income_bracket, age_group, profession) so clients
can compare WTP across persona types.
"""

from __future__ import annotations

from collections import defaultdict


def segment_psm_by(raw: list[dict], dimension: str) -> dict[str, list[dict]]:
    """
    Group Van Westendorp PSM responses by a demographic dimension.

    Args:
        raw: List of PSM response dicts (from collect_psm_responses).
        dimension: Demographic key to segment by (e.g. "income_bracket").

    Returns:
        Dict mapping dimension values to lists of PSM response dicts.
        Personas missing the dimension are grouped under "unknown".
    """
    segments: dict[str, list[dict]] = defaultdict(list)

    for r in raw:
        value = r["demographics"].get(dimension, "unknown")
        segments[value].append(r)

    return dict(segments)


def segment_demand_by(raw: list[dict], dimension: str) -> dict[str, list[dict]]:
    """
    Group Gabor-Granger demand responses by a demographic dimension.

    Args:
        raw: List of demand response dicts (from collect_demand_responses).
        dimension: Demographic key to segment by (e.g. "income_bracket").

    Returns:
        Dict mapping dimension values to lists of demand response dicts.
        Personas missing the dimension are grouped under "unknown".
    """
    segments: dict[str, list[dict]] = defaultdict(list)

    for r in raw:
        value = r["demographics"].get(dimension, "unknown")
        segments[value].append(r)

    return dict(segments)
