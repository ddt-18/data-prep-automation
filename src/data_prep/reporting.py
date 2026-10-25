"""HTML profiling reports.

``ydata-profiling`` is imported lazily so the rest of the package (and its
tests) work without it installed. The report embeds sample rows and value
frequencies from the DataFrame, so the output file is as sensitive as the
input - see the README's privacy section.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from .errors import EmptyOutputError, LoadError
from .names import slugify_filename

logger = logging.getLogger(__name__)

#: Above this many rows the report is built in ``minimal`` mode.
MINIMAL_REPORT_THRESHOLD = 10_000


def build_report(
    df: pd.DataFrame,
    base_filename: str,
    output_folder: str | Path,
    *,
    minimal_threshold: int = MINIMAL_REPORT_THRESHOLD,
    date_stamp: str | None = None,
) -> Path:
    """Write ``<name>_report_<YYYYMMDD>.html`` and return its path."""
    if df.empty:
        raise EmptyOutputError(
            f"Cannot profile an empty dataset for {base_filename!r}."
        )

    try:
        from ydata_profiling import ProfileReport
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise LoadError(
            "ydata-profiling is not installed, so the HTML report cannot be "
            "built. Install it with: pip install -r requirements.txt"
        ) from exc

    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = date_stamp or datetime.now().strftime("%Y%m%d")
    out_path = folder / f"{slugify_filename(base_filename)}_report_{stamp}.html"

    profile = ProfileReport(
        df,
        title=f"Profiling Report for {base_filename}",
        minimal=len(df) > minimal_threshold,
        explorative=True,
        progress_bar=False,
    )
    profile.to_file(out_path, silent=True)
    logger.info("Report saved: %s", out_path)
    return out_path
