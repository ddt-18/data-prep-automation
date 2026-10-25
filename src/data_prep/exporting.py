"""Writing cleaned datasets to disk."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd

from .errors import EmptyOutputError
from .names import slugify_filename

logger = logging.getLogger(__name__)

#: Excel's hard sheet limit. It counts the header row, so a frame with
#: ``EXCEL_ROW_LIMIT - 1`` data rows still fits.
EXCEL_ROW_LIMIT = 1_048_576


@dataclass(frozen=True)
class OutputPaths:
    """Where a cleaned dataset was written (``excel`` is ``None`` if skipped)."""

    csv: Path
    excel: Path | None = None
    notes: list[str] = field(default_factory=list)


def save_outputs(
    df: pd.DataFrame,
    base_filename: str,
    output_folder: str | Path,
    *,
    timestamp: str | None = None,
    write_excel: bool = True,
    allow_empty: bool = False,
    excel_row_limit: int = EXCEL_ROW_LIMIT,
) -> OutputPaths:
    """Save ``df`` as CSV (always) and Excel (when it fits).

    Writing an empty frame raises :class:`EmptyOutputError` unless
    ``allow_empty=True``. The original code happily wrote a 0-row CSV after
    dropping every row and printed a success message, which made data loss look
    like a completed job.
    """
    if df.empty and not allow_empty:
        raise EmptyOutputError(
            f"Refusing to write an empty dataset for {base_filename!r} "
            f"(0 rows, {df.shape[1]} columns). Every row was removed during "
            "cleaning. Review the summary, then pass allow_empty=True if an "
            "empty file really is what you want."
        )

    folder = Path(output_folder)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{slugify_filename(base_filename)}_cleaned_{stamp}"

    notes: list[str] = []
    csv_path = folder / f"{stem}.csv"
    df.to_csv(csv_path, index=False)
    logger.info("Saved CSV: %s", csv_path)

    excel_path: Path | None = None
    if not write_excel:
        notes.append("Excel export disabled")
    elif df.shape[0] + 1 > excel_row_limit:
        notes.append(
            f"skipped Excel export: {df.shape[0]} data rows + 1 header row "
            f"exceeds Excel's limit of {excel_row_limit}"
        )
        logger.warning(notes[-1])
    else:
        candidate = folder / f"{stem}.xlsx"
        try:
            df.to_excel(candidate, index=False, engine="openpyxl")
            excel_path = candidate
            logger.info("Saved Excel: %s", candidate)
        except Exception as exc:  # noqa: BLE001 - reported, not raised
            notes.append(f"Excel export failed: {exc}")
            logger.warning("Excel export failed for %s: %s", base_filename, exc)

    return OutputPaths(csv=csv_path, excel=excel_path, notes=notes)
