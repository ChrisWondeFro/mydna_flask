"""Render the classification breakdown as an in-memory PNG.

Nothing is written to disk. The previous implementation saved to a fixed path
inside ``static/``, so concurrent runs overwrote each other's charts and every
generated image persisted after the request.
"""

from __future__ import annotations

import base64
from io import BytesIO

import matplotlib

matplotlib.use("Agg")  # No display, and safe to import off the main thread.

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

from mydna.core.report import Report  # noqa: E402

# Kept in sync with the custom properties in static/css/mydna.css so the chart
# and the classification groups read as one palette. "Conflicting" sits off the
# red-to-green severity axis deliberately: it is a statement about disagreement
# between submitters, not about severity.
_BUCKET_COLOURS = {
    "pathogenic": "#b4232c",
    "likely-pathogenic": "#c2612f",
    "conflicting": "#7b5ea7",
    "uncertain": "#6b7078",
    "risk-factor": "#b8862b",
    "drug-response": "#35708f",
    "benign": "#2f7d54",
    "likely-benign": "#4a8f68",
    "other": "#7d838b",
}


def render_classification_chart(report: Report) -> str | None:
    """Return a ``data:`` URI for the chart, or None when there is nothing to plot."""
    groups = [group for group in report.groups if group.count]
    if not groups:
        return None

    # Least notable at the top so the most notable sits nearest the axis.
    ordered = sorted(groups, key=lambda group: group.rank, reverse=True)
    labels = [group.label for group in ordered]
    values = [group.count for group in ordered]
    colours = [_BUCKET_COLOURS.get(group.bucket, "#9aa0a8") for group in ordered]

    height = max(2.4, 0.5 * len(ordered) + 1.2)
    figure, axes = plt.subplots(figsize=(8, height), dpi=144)
    try:
        bars = axes.barh(labels, values, color=colours, height=0.62)
        axes.set_xlabel("ClinVar records matched")
        axes.set_title("Matched records by ClinVar classification", pad=12)
        axes.spines[["top", "right"]].set_visible(False)
        axes.grid(axis="x", linestyle=":", alpha=0.4)
        axes.set_axisbelow(True)
        # Counts are whole numbers; the default locator produces 0.5 steps when
        # the largest bar is small.
        axes.xaxis.set_major_locator(MaxNLocator(integer=True))

        offset = max(values) * 0.01 if values else 0
        for bar, value in zip(bars, values, strict=False):
            axes.text(
                bar.get_width() + offset,
                bar.get_y() + bar.get_height() / 2,
                f"{value:,}",
                va="center",
                fontsize=9,
            )
        axes.set_xlim(0, max(values) * 1.12)
        figure.tight_layout()

        buffer = BytesIO()
        figure.savefig(buffer, format="png", bbox_inches="tight")
    finally:
        # `plt.clf()` alone left the figure registered with pyplot, leaking one
        # figure per request.
        plt.close(figure)

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
