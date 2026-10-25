"""Reading datasets from disk.

The notebook originally tried ``utf-8``, then ``latin1``, then ``iso-8859-1``.
That order silently "succeeds" on the wrong encoding because latin-1 can decode
*any* byte sequence, so a UTF-16 file was reported as loaded successfully while
containing nothing but NaN. This module instead:

* honours a byte-order mark,
* only accepts an encoding if the decoded text actually looks like text,
* and raises an actionable error rather than guessing.
"""

from __future__ import annotations

import codecs
import logging
import os
import re
from pathlib import Path

import pandas as pd

from .errors import (
    EmptyFileError,
    EncodingDetectionError,
    LoadError,
    UnsupportedFormatError,
)

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: tuple[str, ...] = (".csv", ".xlsx", ".xls", ".json", ".parquet")

# Tried in order. latin-1 is a last resort because it can decode anything, so it
# is only used after the stricter candidates have been rejected.
CSV_ENCODING_CANDIDATES: tuple[str, ...] = ("utf-8", "cp1252", "latin-1")

# UTF-32 BOMs must be checked before UTF-16, because the UTF-32-LE BOM starts
# with the UTF-16-LE BOM bytes.
_BOM_ENCODINGS: tuple[tuple[bytes, str], ...] = (
    (codecs.BOM_UTF32_LE, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF16_LE, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16"),
)

_SAMPLE_BYTES = 1024 * 1024
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_CONTROL_CHAR_TOLERANCE = 0.01
_EXCEL_LOCK_PREFIX = "~$"


def list_data_files(folder: str | os.PathLike[str]) -> list[Path]:
    """Return supported dataset files in ``folder``, sorted by name.

    Sorting matters: the notebook lets you pick files by number, and
    ``os.listdir`` order is filesystem-dependent, so "file 3" used to mean
    different things on different machines. Excel lock files (``~$book.xlsx``)
    are skipped because they are not datasets.
    """
    directory = Path(folder)
    if not directory.is_dir():
        raise LoadError(f"Not a directory: {directory}")

    files = []
    for entry in directory.iterdir():
        name = entry.name
        if name.startswith(_EXCEL_LOCK_PREFIX) or name.startswith("."):
            continue
        if entry.is_file() and entry.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(entry)
    return sorted(files, key=lambda p: p.name.lower())


def _read_sample(path: Path, limit: int = _SAMPLE_BYTES) -> bytes:
    with open(path, "rb") as handle:
        return handle.read(limit)


def _bom_encoding(raw: bytes) -> str | None:
    for bom, encoding in _BOM_ENCODINGS:
        if raw.startswith(bom):
            return encoding
    return None


def _looks_like_text(raw: bytes, encoding: str) -> tuple[bool, str]:
    """Decode ``raw`` and decide whether the result is plausible text."""
    try:
        text = raw.decode(encoding)
    except (UnicodeDecodeError, LookupError) as exc:
        return False, f"cannot decode: {exc}"

    if "\x00" in text:
        # The classic symptom of reading a UTF-16 file as a single-byte
        # encoding: every other byte is NUL.
        return False, "decoded text contains NUL characters (probably UTF-16)"

    if text:
        controls = len(_CONTROL_CHARS.findall(text))
        if controls / len(text) > _CONTROL_CHAR_TOLERANCE:
            return False, f"{controls} control characters in sample"

    return True, ""


def detect_csv_encoding(path: str | os.PathLike[str]) -> str:
    """Pick the most plausible encoding for a CSV file.

    Raises :class:`EmptyFileError` for a 0-byte file and
    :class:`EncodingDetectionError` when no candidate looks like text.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise LoadError(f"File not found: {file_path}")
    if file_path.stat().st_size == 0:
        raise EmptyFileError(
            f"{file_path.name} is empty (0 bytes). Check that the download or "
            "export actually wrote data."
        )

    raw = _read_sample(file_path)
    bom = _bom_encoding(raw)
    if bom is not None:
        logger.info("Detected %s byte-order mark in %s", bom, file_path.name)
        return bom

    reasons: list[str] = []
    for encoding in CSV_ENCODING_CANDIDATES:
        ok, reason = _looks_like_text(raw, encoding)
        if ok:
            logger.info("Using %s to read %s", encoding, file_path.name)
            return encoding
        reasons.append(f"{encoding}: {reason}")

    hint = ""
    if any("UTF-16" in reason for reason in reasons):
        hint = (
            " The file looks like UTF-16 (common for 'Unicode Text' exports "
            "from Excel); re-save it as UTF-8 CSV, or pass encoding='utf-16'."
        )
    raise EncodingDetectionError(
        "Could not determine the text encoding of "
        f"{file_path.name}. Tried: {'; '.join(reasons)}.{hint}"
    )


def _read_csv(path: Path, encoding: str | None) -> pd.DataFrame:
    if encoding is not None:
        candidates = (encoding,)
    else:
        candidates = (detect_csv_encoding(path),)

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            return pd.read_csv(path, encoding=candidate)
        except UnicodeDecodeError as exc:  # explicit override was wrong
            last_error = exc
            logger.warning("Decoding %s with %s failed: %s", path.name, candidate, exc)

    raise EncodingDetectionError(
        f"Could not decode {path.name} with encoding={encoding!r}: {last_error}"
    )


def _read_json(path: Path) -> pd.DataFrame:
    """Read both a single JSON document and line-delimited JSON (JSON Lines)."""
    try:
        return pd.read_json(path)
    except ValueError as exc:
        message = str(exc)
        # pd.read_json expects one JSON document; .json files exported as one
        # record per line fail with "Trailing data".
        if "Trailing data" not in message and "Extra data" not in message:
            raise
        logger.info("%s looks like JSON Lines; retrying with lines=True", path.name)
    try:
        return pd.read_json(path, lines=True)
    except ValueError as exc:
        raise LoadError(
            f"Could not parse {path.name} as JSON or JSON Lines: {exc}"
        ) from exc


def load_table(
    path: str | os.PathLike[str],
    *,
    encoding: str | None = None,
    sheet_name: str | int = 0,
) -> pd.DataFrame:
    """Load a CSV, Excel, JSON/JSON Lines or Parquet file into a DataFrame.

    ``encoding`` forces the encoding for CSV files; leave it as ``None`` to
    detect it. ``sheet_name`` selects the Excel sheet (default: the first one).

    Only the requested file is read; no rows are dropped or converted here, so
    the DataFrame mirrors the file as closely as pandas allows.
    """
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    if not file_path.is_file():
        raise LoadError(f"File not found: {file_path}")
    if suffix not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"Unsupported file type {suffix!r} for {file_path.name}. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    logger.info("Loading %s", file_path)
    try:
        if suffix == ".csv":
            df = _read_csv(file_path, encoding)
        elif suffix in {".xlsx", ".xls"}:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        elif suffix == ".json":
            df = _read_json(file_path)
        else:  # pragma: no cover - suffix is validated above
            df = pd.read_parquet(file_path)
    except ImportError as exc:
        raise LoadError(
            f"Missing optional dependency for {suffix} files: {exc}. "
            "Install the extras from requirements.txt "
            "(pyarrow for Parquet, xlrd for .xls)."
        ) from exc
    except pd.errors.EmptyDataError as exc:
        raise EmptyFileError(
            f"{file_path.name} has no columns to read. Is it really a CSV?"
        ) from exc
    except (LoadError, UnsupportedFormatError, EmptyFileError):
        raise
    except Exception as exc:
        raise LoadError(f"Could not read {file_path.name}: {exc}") from exc

    if df.columns.empty:
        raise EmptyFileError(f"{file_path.name} was read but has no columns.")

    logger.info("Loaded %s with shape %s", file_path.name, df.shape)
    return df
