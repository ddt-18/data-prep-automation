"""Cleaning a DataFrame, with a structured record of everything that changed.

Design rules that keep the data correct:

* **Nothing is converted to a number unless you ask.** The original notebook ran
  ``pd.to_numeric`` over every column, which turned ``"01234"`` into ``1234`` and
  ``"007"`` into ``7``. Here the default is ``numeric_coercion="none"``; opting
  into ``"safe"`` still skips identifier-like columns and reports why.
* **Missing values are actually filled.** The original used
  ``df[col].fillna(..., inplace=True)`` on a temporary Series, which pandas 3
  ignores entirely while the code still printed "filled".
* **Column names stay unique.** ``Total Price`` and ``Total_Price`` no longer
  collapse into one column.
* **Every step is recorded** in :class:`CleaningSummary` so a run can be audited
  or turned into a before/after report.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Literal, Sequence

import pandas as pd

from .names import build_unique_names

logger = logging.getLogger(__name__)

MissingStrategy = Literal["none", "drop", "fill"]
NumericCoercion = Literal["none", "safe"]

# Tokens that mark a column as an identifier. Matched against name *tokens*,
# never substrings, so "paid", "valid", "width" and "avoid" are not mistaken
# for IDs (the original code excluded all of those via substring matching).
IDENTIFIER_TOKENS = frozenset(
    {
        "id", "ids", "uuid", "guid", "code", "zip", "postal", "postcode",
        "phone", "tel", "mobile", "sku", "isbn", "fips", "npi", "ssn",
    }
)

CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_LEADING_ZERO = re.compile(r"^0\d+$")
_LONG_DIGITS = re.compile(r"^\d{12,}$")
_QUOTE_WRAPPED = re.compile(r"""^["'].*["']$""")

#: Warn when a column being filled is at least this fraction missing.
FILL_WARNING_THRESHOLD = 0.5
#: Warn when dropping missing values removes at least this fraction of rows.
DROP_WARNING_THRESHOLD = 0.5


@dataclass(frozen=True)
class CleaningOptions:
    """What cleaning to do. Defaults are deliberately conservative."""

    missing_values: MissingStrategy = "none"
    drop_duplicates: bool = False
    duplicate_subset: Sequence[str] | None = None
    duplicate_keep: Literal["first", "last"] = "first"
    fill_numeric: Literal["mean", "median"] = "mean"
    fill_categorical: Literal["mode", "constant"] = "mode"
    fill_constant: Any = "Unknown"
    numeric_coercion: NumericCoercion = "none"

    def __post_init__(self) -> None:
        if self.missing_values not in ("none", "drop", "fill"):
            raise ValueError(
                f"missing_values must be 'none', 'drop' or 'fill', got {self.missing_values!r}"
            )
        if self.numeric_coercion not in ("none", "safe"):
            raise ValueError(
                "numeric_coercion must be 'none' or 'safe', got "
                f"{self.numeric_coercion!r}"
            )
        if self.fill_numeric not in ("mean", "median"):
            raise ValueError(f"fill_numeric must be 'mean' or 'median', got {self.fill_numeric!r}")
        if self.fill_categorical not in ("mode", "constant"):
            raise ValueError(
                "fill_categorical must be 'mode' or 'constant', got "
                f"{self.fill_categorical!r}"
            )
        if self.duplicate_keep not in ("first", "last"):
            raise ValueError(
                f"duplicate_keep must be 'first' or 'last', got {self.duplicate_keep!r}"
            )


@dataclass
class ColumnRename:
    original: str
    cleaned: str
    dtype_before: str
    dtype_after: str

    def to_dict(self) -> dict[str, str]:
        return {
            "original": self.original,
            "cleaned": self.cleaned,
            "dtype_before": self.dtype_before,
            "dtype_after": self.dtype_after,
        }


@dataclass
class FillRecord:
    column: str
    strategy: str
    value: Any
    count: int
    missing_fraction: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "strategy": self.strategy,
            "value": _json_safe(self.value),
            "count": int(self.count),
            "missing_fraction": round(float(self.missing_fraction), 4),
        }


@dataclass
class CoercionRecord:
    column: str
    converted: bool
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "converted": bool(self.converted),
            "reason": self.reason,
        }


@dataclass
class CleaningSummary:
    """Everything ``clean_data`` changed, in a JSON-friendly shape."""

    rows_in: int = 0
    rows_out: int = 0
    columns_in: int = 0
    columns_out: int = 0
    duplicates_removed: int = 0
    duplicate_subset: list[str] | None = None
    rows_dropped_missing: int = 0
    null_counts: dict[str, int] = field(default_factory=dict)
    renames: list[ColumnRename] = field(default_factory=list)
    collisions: list[str] = field(default_factory=list)
    fills: list[FillRecord] = field(default_factory=list)
    coercions: list[CoercionRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def renamed_columns(self) -> dict[str, str]:
        return {rename.original: rename.cleaned for rename in self.renames}

    def to_dict(self) -> dict[str, Any]:
        """Return a ``json.dumps``-able dict (no numpy scalars)."""
        return {
            "rows_in": int(self.rows_in),
            "rows_out": int(self.rows_out),
            "rows_removed": int(self.rows_in - self.rows_out),
            "columns_in": int(self.columns_in),
            "columns_out": int(self.columns_out),
            "duplicates_removed": int(self.duplicates_removed),
            "duplicate_subset": list(self.duplicate_subset) if self.duplicate_subset else None,
            "rows_dropped_missing": int(self.rows_dropped_missing),
            "null_counts": {k: int(v) for k, v in self.null_counts.items()},
            "renames": [rename.to_dict() for rename in self.renames],
            "collisions": list(self.collisions),
            "fills": [fill.to_dict() for fill in self.fills],
            "coercions": [coercion.to_dict() for coercion in self.coercions],
            "warnings": list(self.warnings),
        }

    def to_lines(self) -> list[str]:
        """Human-readable one-liners, for notebooks and log files."""
        lines = [
            f"rows: {self.rows_in} -> {self.rows_out} "
            f"({self.rows_in - self.rows_out} removed)",
            f"columns: {self.columns_in} -> {self.columns_out} "
            f"({len(self.renames)} renamed)",
        ]
        if self.duplicates_removed:
            scope = (
                f"keyed on {', '.join(self.duplicate_subset)}"
                if self.duplicate_subset
                else "all columns"
            )
            lines.append(f"duplicate rows removed: {self.duplicates_removed} ({scope})")
        else:
            lines.append("duplicate rows removed: 0")
        if self.rows_dropped_missing:
            lines.append(f"rows dropped for missing values: {self.rows_dropped_missing}")
        for fill in self.fills:
            lines.append(
                f"filled {fill.column}: {fill.strategy}={_json_safe(fill.value)!r} "
                f"({fill.count} cells, column was {fill.missing_fraction:.0%} empty)"
            )
        for coercion in self.coercions:
            if coercion.converted:
                lines.append(f"converted {coercion.column} to numeric")
            else:
                lines.append(f"left {coercion.column} as text ({coercion.reason})")
        collisions = f" -> {', '.join(self.collisions)}" if self.collisions else ""
        lines.append(f"column name collisions resolved: {len(self.collisions)}{collisions}")
        lines.extend(f"WARNING: {warning}" for warning in self.warnings)
        return lines


def _json_safe(value: Any) -> Any:
    """Convert numpy/pandas scalars into plain Python values."""
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    item = getattr(value, "item", None)
    if callable(item) and getattr(value, "ndim", None) == 0:
        try:
            return item()
        except (ValueError, TypeError):  # pragma: no cover - defensive
            return str(value)
    return value


def is_text_like(series: pd.Series) -> bool:
    """True for columns holding text (object/string), not numbers/bools/dates."""
    if pd.api.types.is_bool_dtype(series):
        return False
    if pd.api.types.is_numeric_dtype(series):
        return False
    if pd.api.types.is_datetime64_any_dtype(series):
        return False
    return True


def identifier_reason(name: object, series: pd.Series) -> str | None:
    """Return why ``series`` must stay text, or ``None`` if it is safe to convert.

    Checks the column *name* first (cheap), then the values, so a column called
    ``zip`` is protected even when every value happens to be parseable.
    """
    spaced = CAMEL_CASE_BOUNDARY.sub("_", str(name))
    tokens = {token for token in re.split(r"[^0-9A-Za-z]+", spaced.lower()) if token}
    matched = sorted(tokens & IDENTIFIER_TOKENS)
    if matched:
        return f"column name looks like an identifier ('{matched[0]}')"

    if not is_text_like(series):
        return None

    values = series.dropna().astype(str)
    if values.empty:
        return None
    if values.str.match(_LEADING_ZERO).mean() > 0.2:
        return "values have leading zeros"
    if values.str.match(_LONG_DIGITS).mean() > 0.2:
        return "values are long digit strings (likely identifiers)"
    if values.str.match(_QUOTE_WRAPPED).mean() > 0.5:
        return "values are wrapped in quote characters"
    return None


def _fill_value(series: pd.Series, options: CleaningOptions) -> tuple[Any, str] | None:
    """Pick the fill value for one column, or ``None`` if it cannot be filled."""
    numeric = pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(
        series
    )
    if numeric:
        value = series.median() if options.fill_numeric == "median" else series.mean()
        if pd.isna(value):
            return None
        return value, options.fill_numeric

    if options.fill_categorical == "constant":
        return options.fill_constant, "constant"

    modes = series.mode(dropna=True)
    if modes.empty:
        # Nothing to learn from an all-empty column. Text can still take the
        # constant placeholder (as the original notebook did); a date column
        # cannot, so it is left alone and reported.
        if is_text_like(series):
            return options.fill_constant, "constant"
        return None
    return modes.iloc[0], "mode"


def _apply_fill(df: pd.DataFrame, column: str, value: Any) -> str | None:
    """Fill one column in place. Returns an error message on failure."""
    series = df[column]
    try:
        df[column] = series.fillna(value)
    except (TypeError, ValueError) as exc:
        # e.g. an integer-backed nullable column cannot hold 1.5.
        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(
            series
        ):
            df[column] = series.astype("float64").fillna(float(value))
            return f"column {column!r} was cast to float to hold {value!r} ({exc})"
        return f"could not fill column {column!r}: {exc}"
    return None


def _coerce_safely(series: pd.Series) -> tuple[pd.Series | None, str]:
    """Convert a text column to numbers only if nothing is lost."""
    converted = pd.to_numeric(series, errors="coerce")
    new_missing = int(converted.isna().sum()) - int(series.isna().sum())
    if new_missing > 0:
        return None, f"{new_missing} value(s) are not numeric"
    return converted, ""


def clean_data(
    df: pd.DataFrame, options: CleaningOptions | None = None
) -> tuple[pd.DataFrame, CleaningSummary]:
    """Clean ``df`` and describe every change.

    Returns ``(cleaned_dataframe, summary)``. The input frame is never mutated.

    The steps run in a fixed order: rename columns, remove duplicates, handle
    missing values, then (optionally) convert text to numbers. Deduplication
    happens *before* filling so duplicates are matched on the values that were
    actually in the file.
    """
    options = options or CleaningOptions()
    original = df
    summary = CleaningSummary(
        rows_in=int(len(original)),
        columns_in=int(original.shape[1]),
        duplicate_subset=list(options.duplicate_subset) if options.duplicate_subset else None,
    )
    working = original.copy()
    before_dtypes = {column: str(dtype) for column, dtype in working.dtypes.items()}
    original_columns = list(working.columns)

    # 1. Column names: safe, and guaranteed unique.
    cleaned_names, renamed, collisions = build_unique_names(original_columns)
    working.columns = cleaned_names
    lookup = dict(zip(original_columns, cleaned_names))
    summary.collisions = collisions

    for cleaned in collisions:
        summary.warnings.append(
            f"different source columns were both named {cleaned!r}; "
            "the later one was suffixed to keep the names unique"
        )

    # Summaries use cleaned names, so record the input's nulls under those names.
    summary.null_counts = {
        column: int(count) for column, count in working.isna().sum().items()
    }

    # 2. Duplicates, optionally on a key instead of every column.
    if options.drop_duplicates:
        subset = None
        if options.duplicate_subset:
            subset = []
            for requested in options.duplicate_subset:
                resolved = lookup.get(requested, requested)
                if resolved not in working.columns:
                    raise ValueError(
                        f"duplicate_subset column {requested!r} is not in the dataset. "
                        f"Available columns: {list(working.columns)}"
                    )
                subset.append(resolved)
            summary.duplicate_subset = subset

        before = len(working)
        keep = options.duplicate_keep
        working = working.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)
        summary.duplicates_removed = int(before - len(working))
        if not summary.duplicates_removed:
            scope = f"keyed on {subset}" if subset else "across all columns"
            summary.warnings.append(
                f"no duplicate rows found {scope}; "
                "if you expected duplicates, pass duplicate_subset to compare "
                "only the identifying columns"
            )

    # 3. Missing values.
    rows_before_missing = len(working)
    if options.missing_values == "drop":
        working = working.dropna(axis=0, how="any").reset_index(drop=True)
        summary.rows_dropped_missing = int(rows_before_missing - len(working))
        dropped_fraction = (
            summary.rows_dropped_missing / rows_before_missing
            if rows_before_missing
            else 0.0
        )
        if dropped_fraction >= DROP_WARNING_THRESHOLD:
            top = sorted(
                summary.null_counts.items(), key=lambda item: item[1], reverse=True
            )[:3]
            worst = ", ".join(f"{name} ({count} nulls)" for name, count in top if count)
            summary.warnings.append(
                f"dropping rows with any missing value removed "
                f"{summary.rows_dropped_missing} of {rows_before_missing} rows "
                f"({dropped_fraction:.0%}). Most incomplete columns: {worst or 'n/a'}. "
                "Consider per-column rules instead of dropping whole rows."
            )

    elif options.missing_values == "fill":
        for column in working.columns:
            series = working[column]
            missing = int(series.isna().sum())
            if not missing:
                continue
            fraction = missing / len(series) if len(series) else 0.0
            chosen = _fill_value(series, options)
            if chosen is None:
                summary.warnings.append(
                    f"column {column!r} is entirely empty for its type and was "
                    "left unchanged"
                )
                continue
            value, strategy = chosen
            problem = _apply_fill(working, column, value)
            if problem:
                summary.warnings.append(problem)
                continue
            summary.fills.append(
                FillRecord(
                    column=column,
                    strategy=strategy,
                    value=_json_safe(value),
                    count=missing,
                    missing_fraction=fraction,
                )
            )
            if fraction >= FILL_WARNING_THRESHOLD:
                summary.warnings.append(
                    f"column {column!r} was {fraction:.0%} missing and was filled "
                    f"with {strategy}={_json_safe(value)!r}; values that were "
                    "never recorded now look real"
                )

    # 4. Optional, explicit numeric conversion.
    if options.numeric_coercion == "safe":
        for column in working.columns:
            series = working[column]
            if not is_text_like(series):
                continue
            reason = identifier_reason(column, series)
            if reason:
                summary.coercions.append(
                    CoercionRecord(column, converted=False, reason=reason)
                )
                continue
            converted, reason = _coerce_safely(series)
            if converted is None:
                summary.coercions.append(
                    CoercionRecord(column, converted=False, reason=reason)
                )
                continue
            working[column] = converted
            summary.coercions.append(CoercionRecord(column, converted=True))

    summary.renames = [
        ColumnRename(
            original=original_name,
            cleaned=cleaned_name,
            dtype_before=before_dtypes.get(original_name, ""),
            dtype_after=str(working[cleaned_name].dtype),
        )
        for original_name, cleaned_name in renamed
        if cleaned_name in working.columns
    ]
    summary.rows_out = int(len(working))
    summary.columns_out = int(working.shape[1])

    if summary.rows_out == 0:
        summary.warnings.append(
            "the cleaned dataset has 0 rows; writing it is refused by default "
            "because an empty file looks like success"
        )

    logger.info(
        "Cleaned %s -> %s rows, %s -> %s columns",
        summary.rows_in,
        summary.rows_out,
        summary.columns_in,
        summary.columns_out,
    )
    return working, summary
