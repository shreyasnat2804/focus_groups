"""
Chart generation for WTP analysis.

Produces Van Westendorp PSM curve plots and Gabor-Granger demand curve
charts using matplotlib.
"""

from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.figure


def plot_van_westendorp(
    curves: dict,
    price_pts: dict,
    title: str = "Van Westendorp Price Sensitivity Meter",
) -> matplotlib.figure.Figure:
    """
    Plot the four Van Westendorp PSM curves with optimal price and acceptable range.

    Args:
        curves: Output of compute_psm_curves (price_points + 4 curve arrays).
        price_pts: Output of find_price_points (optimal_price + acceptable_range).
        title: Chart title.

    Returns:
        matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    prices = curves["price_points"]

    ax.plot(prices, curves["too_cheap"], label="Too Cheap", color="#e74c3c", linewidth=2)
    ax.plot(prices, curves["cheap"], label="Bargain", color="#f39c12", linewidth=2)
    ax.plot(prices, curves["expensive"], label="Expensive", color="#3498db", linewidth=2)
    ax.plot(prices, curves["too_expensive"], label="Too Expensive", color="#8e44ad", linewidth=2)

    # Mark optimal price point
    opp = price_pts["optimal_price"]
    ax.axvline(x=opp, color="#2c3e50", linestyle="--", linewidth=1.5, label=f"Optimal: ${opp:.0f}")

    # Shade acceptable range
    low, high = price_pts["acceptable_range"]
    ax.axvspan(low, high, alpha=0.1, color="#27ae60", label=f"Acceptable: ${low:.0f}-${high:.0f}")

    ax.set_xlabel("Price ($)")
    ax.set_ylabel("% of Respondents")
    ax.set_title(title)
    ax.legend(loc="center right")
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    return fig


def plot_demand_curve(
    curve: dict,
    title: str = "Gabor-Granger Demand Curve",
) -> matplotlib.figure.Figure:
    """
    Plot the Gabor-Granger demand curve showing % who would buy at each price.

    Args:
        curve: Output of compute_demand_curve (price_points + demand_pct).
        title: Chart title.

    Returns:
        matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    prices = curve["price_points"]
    demand = curve["demand_pct"]

    ax.plot(prices, demand, marker="o", color="#2980b9", linewidth=2, markersize=8)
    ax.fill_between(prices, demand, alpha=0.15, color="#2980b9")

    # Annotate each point
    for p, d in zip(prices, demand):
        ax.annotate(
            f"{d:.0f}%",
            (p, d),
            textcoords="offset points",
            xytext=(0, 12),
            ha="center",
            fontsize=9,
        )

    ax.set_xlabel("Price ($)")
    ax.set_ylabel("% Would Purchase")
    ax.set_title(title)
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    return fig


def plot_segmented_demand(
    segment_curves: dict[str, dict],
    title: str = "Demand Curve by Segment",
) -> matplotlib.figure.Figure:
    """
    Plot overlaid demand curves for each demographic segment.

    Args:
        segment_curves: Dict mapping segment name to demand curve dict.
        title: Chart title.

    Returns:
        matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    colors = ["#e74c3c", "#3498db", "#27ae60", "#f39c12", "#8e44ad", "#1abc9c"]

    for i, (name, curve) in enumerate(sorted(segment_curves.items())):
        color = colors[i % len(colors)]
        ax.plot(
            curve["price_points"],
            curve["demand_pct"],
            marker="o",
            color=color,
            linewidth=2,
            markersize=6,
            label=name,
        )

    ax.set_xlabel("Price ($)")
    ax.set_ylabel("% Would Purchase")
    ax.set_title(title)
    ax.set_ylim(0, 105)
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    return fig
