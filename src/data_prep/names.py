"""Column-name and filename normalisation.

Two rules matter for correctness here:

1. Column names are made safe and **unique**. Two different source columns
   (``Total Price`` and ``Total_Price``) must never end up with the same name,
   because duplicate column names make pandas return a DataFrame instead of a
   Series and crash groupby/reporting later.
2. Column names are used to build output filenames, so anything that could
   change the path (``/``, ``\\``, ``..``) is replaced.
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence

_WHITESPACE = re.compile(r"\s+")
_UNSAFE_CHARS = re.compile(r"[^0-9A-Za-z_]+")
_REPEATED_UNDERSCORES = re.compile(r"_{2,}")

_FILENAME_UNSAFE = re.compile(r"[^0-9A-Za-z_-]+")
_FILENAME_SEPARATORS = re.compile(r"[-_]{2,}")

# Public constant so tests and callers can reference the fallback.
FALLBACK_COLUMN_NAME = "column"
FALLBACK_FILENAME = "column"
MAX_FILENAME_LENGTH = 80


def sanitize_column_name(name: object) -> str:
    """Turn any column label into a safe, non-empty ``snake_case``-ish name.

    Non-string labels are converted with ``str()`` first, so an Excel header of
    ``2024`` becomes the column ``"2024"`` instead of raising
    ``AttributeError: 'int' object has no attribute 'strip'``.

        >>> sanitize_column_name("Total  Price ")
        'Total_Price'
        >>> sanitize_column_name("a/b")
        'a_b'
        >>> sanitize_column_name(2024)
        '2024'
    """
    text = str(name).strip()
    text = _WHITESPACE.sub("_", text)
    text = _UNSAFE_CHARS.sub("_", text)
    text = _REPEATED_UNDERSCORES.sub("_", text)
    text = text.strip("_")
    return text or FALLBACK_COLUMN_NAME


def build_unique_names(
    names: Sequence[object], taken: Iterable[str] = ()
) -> tuple[list[str], list[tuple[object, str]], list[str]]:
    """Sanitize ``names`` and make them unique.

    Returns ``(cleaned_names, renamed, collisions)`` where ``renamed`` is a list
    of ``(original, cleaned)`` pairs that changed, and ``collisions`` lists the
    cleaned names that had to be suffixed because of a clash.

    Names keep the order of the input, which matters because column order is
    part of a dataset's contract.
    """
    used = {str(name) for name in taken}
    cleaned_names: list[str] = []
    renamed: list[tuple[object, str]] = []
    collisions: list[str] = []

    for original in names:
        candidate = sanitize_column_name(original)
        final = candidate
        suffix = 2
        while final in used:
            if candidate not in collisions:
                collisions.append(candidate)
            final = f"{candidate}_{suffix}"
            suffix += 1
        used.add(final)
        cleaned_names.append(final)
        if final != original:
            renamed.append((original, final))

    return cleaned_names, renamed, collisions


def slugify_filename(text: object, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """Convert arbitrary text into a safe single path segment.

    Used for plot filenames, where a column named ``a/b`` or
    ``../../escaped`` must not be able to create directories or escape the
    output folder.

        >>> slugify_filename("Pickup Location")
        'Pickup_Location'
        >>> slugify_filename("a/b")
        'a_b'
        >>> slugify_filename("../../escaped")
        'escaped'
    """
    slug = _FILENAME_UNSAFE.sub("_", str(text).strip())
    slug = _FILENAME_SEPARATORS.sub("_", slug)
    slug = slug.strip("_-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("_-")
    return slug or FALLBACK_FILENAME


class FilenameRegistry:
    """Hands out unique slugs so two columns never overwrite one PNG."""

    def __init__(self) -> None:
        self._used: set[str] = set()

    def slug(self, text: object) -> str:
        base = slugify_filename(text)
        candidate = base
        suffix = 2
        while candidate.lower() in self._used:
            candidate = f"{base}_{suffix}"
            suffix += 1
        self._used.add(candidate.lower())
        return candidate
