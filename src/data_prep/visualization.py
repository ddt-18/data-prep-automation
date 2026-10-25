"""Bar and pie charts for categorical columns.

Charts are drawn with matplotlib only. The original used seaborn for a single
bar plot; dropping it removes a dependency and the "passing ``palette`` without
``hue``" deprecation warning, while producing the same top-10 chart.

Two correctness details:

* Values are counted on a **sample** when one is requested, so the chart title
  says so - otherwise "Top 10 Vehicle Type" silently describes only 50,000 of
  150,000 rows.
* Column names are never used directly in a filename; they are slugified, so a
  column called ``a/b`` no longer crashes the run.
"""

from __future__ import annotations

import itertools
import logging
import re
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from .names import FilenameRegistry, slugify_filename

logger = logging.getLogger(__name__)

DEFAULT_FIGURE_SIZE = (10, 6)
DEFAULT_COLORS = ("#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF", "#4D5360")

#: Auto-selection skips columns whose *name tokens* look like free text or
#: identifiers. Token matching (not substring matching) keeps "paid", "valid",
#: "width" and "avoid" eligible - the original excluded them because they
#: contain "id".
EXCLUDED_TOKENS = frozenset(
    {
        "id", "ids", "uuid", "guid", "desc", "description", "number", "num",
        "phone", "tel", "mobile", "contact", "email", "name", "address",
        "comment", "notes", "remark",
    }
)

BAR_MIN_CATEGORIES = 5
BAR_MAX_CATEGORIES = 100
PIE_MIN_CATEGORIES = 2
PIE_MAX_CATEGORIES = 10
TOP_N = 10


def _name_tokens(name: object) -> set[str]:
    """Split a column name into lowercase words.

    Splits on any non-alphanumeric character *and* on camelCase boundaries, so
    ``Booking ID``, ``booking_id`` and ``VendorID`` all yield an ``id`` token,
    while ``paid`` stays a single word.
    """
    text = str(name)
    spaced = "".join(
        ("_" + char) if index and char.isupper() and text[index - 1].islower() else char
        for index, char in enumerate(text)
    )
    tokens = set()
    for chunk in re.split(r"[^0-9A-Za-z]+", spaced):
        cleaned = chunk.lower()
        if cleaned:
            tokens.add(cleaned)
    return tokens


def excluded_column(name: object) -> bool:
    """True when auto-selection should ignore ``name``."""
    return bool(_name_tokens(name) & EXCLUDED_TOKENS)


def select_plot_frame(df: pd.DataFrame, sample_size: int | None) -> tuple[pd.DataFrame, bool]:
    """Return ``(frame_for_plots, was_sampled)``."""
    if sample_size is None or sample_size >= len(df) or sample_size <= 0:
        return df, False
    sampled = df.sample(n=sample_size, random_state=42)
    logger.info("Using a sample of %s rows for visualization", sample_size)
    return sampled, True


def categorical_columns(df: pd.DataFrame) -> list[str]:
    """Object/string/category columns, across pandas 2.x and 3.x.

    pandas 3 reads text as a ``str`` dtype, so ``include=["object"]`` alone
    would start returning nothing once the deprecation lands.
    """
    selected = df.select_dtypes(include=["object", "category", "string"]).columns
    return [str(column) for column in selected]


def auto_select_columns(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Pick ``(bar_columns, pie_columns)`` when the user does not choose."""
    candidates = [name for name in categorical_columns(df) if not excluded_column(name)]
    pie_columns = [
        name for name in candidates if PIE_MIN_CATEGORIES <= df[name].nunique() <= PIE_MAX_CATEGORIES
    ][:2]
    bar_columns = [
        name for name in candidates if BAR_MIN_CATEGORIES <= df[name].nunique() <= BAR_MAX_CATEGORIES
    ][:2]
    return bar_columns, pie_columns


def _cycled(colors: Sequence[str], count: int) -> list[str]:
    return list(itertools.islice(itertools.cycle(colors), count))


def _title(label: str, column: str, sampled: bool, sample_rows: int) -> str:
    if sampled:
        return f"{label} {column} (n={sample_rows:,} sample)"
    return f"{label} {column}"


def make_charts(
    df: pd.DataFrame,
    base_filename: str,
    output_folder: str | Path,
    *,
    bar_columns: Iterable[str] = (),
    pie_columns: Iterable[str] = (),
    sample_size: int | None = None,
    figure_size: tuple[int, int] = DEFAULT_FIGURE_SIZE,
    colors: Sequence[str] = DEFAULT_COLORS,
) -> tuple[list[Path], list[str]]:
    """Write bar/pie PNGs and return ``(paths_written, notes)``.

    Columns that cannot be charted are skipped with a note instead of raising,
    so one odd column cannot abort a batch.
    """
    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    plot_frame, sampled = select_plot_frame(df, sample_size)
    notes: list[str] = []
    written: list[Path] = []

    if plot_frame.empty:
        notes.append("no rows available for charts")
        return written, notes

    bar_columns = list(bar_columns)
    pie_columns = list(pie_columns)
    if not bar_columns and not pie_columns:
        # Same behaviour as the original notebook: when the user declines to
        # choose, pick a couple of sensible categorical columns.
        bar_columns, pie_columns = auto_select_columns(plot_frame)
        if not (bar_columns or pie_columns):
            notes.append("no suitable categorical columns for charts")
            return written, notes
        notes.append(
            "auto-selected chart columns: "
            + ", ".join(bar_columns + pie_columns)
        )

    plot_folder = Path(output_folder) / f"{slugify_filename(base_filename)}_plots"
    plot_folder.mkdir(parents=True, exist_ok=True)
    # Separate registries: the bar_/pie_ prefixes already make the two names
    # distinct, so a column used for both kinds keeps its documented filenames.
    bar_registry = FilenameRegistry()
    pie_registry = FilenameRegistry()

    for column in bar_columns:
        column = str(column)
        if column not in plot_frame.columns:
            notes.append(f"bar chart skipped: no column named {column!r}")
            continue
        counts = plot_frame[column].dropna().value_counts().nlargest(TOP_N)
        if counts.empty:
            notes.append(f"bar chart skipped: column {column!r} has no values")
            continue

        fig, ax = plt.subplots(figsize=figure_size)
        try:
            positions = range(len(counts))
            ax.barh(list(positions), counts.to_numpy(), color=_cycled(colors, len(counts)))
            ax.set_yticks(list(positions))
            ax.set_yticklabels([str(label) for label in counts.index])
            ax.invert_yaxis()
            ax.set_xlabel("count")
            ax.set_title(_title(f"Top {TOP_N}", column, sampled, len(plot_frame)))
            fig.tight_layout()
            path = plot_folder / f"bar_{bar_registry.slug(column)}.png"
            fig.savefig(path)
            written.append(path)
            logger.info("Wrote %s", path)
        finally:
            plt.close(fig)

    for column in pie_columns:
        column = str(column)
        if column not in plot_frame.columns:
            notes.append(f"pie chart skipped: no column named {column!r}")
            continue
        counts = plot_frame[column].dropna().value_counts()
        if not PIE_MIN_CATEGORIES <= len(counts) <= PIE_MAX_CATEGORIES:
            notes.append(
                f"pie chart skipped: column {column!r} has {len(counts)} distinct "
                f"values (a pie needs {PIE_MIN_CATEGORIES}-{PIE_MAX_CATEGORIES})"
            )
            continue

        fig, ax = plt.subplots(figsize=figure_size)
        try:
            ax.pie(
                counts.to_numpy(),
                labels=[str(label) for label in counts.index],
                autopct="%1.1f%%",
                colors=_cycled(colors, len(counts)),
                startangle=90,
            )
            ax.set_title(_title("Distribution of", column, sampled, len(plot_frame)))
            fig.tight_layout()
            path = plot_folder / f"pie_{pie_registry.slug(column)}.png"
            fig.savefig(path)
            written.append(path)
            logger.info("Wrote %s", path)
        finally:
            plt.close(fig)

    return written, notes
