"""Parsing for the interactive prompts.

These functions are pure: they take the text a user typed and return a value or
raise :class:`PromptError`. The notebook's ``input()`` loop catches that error
and asks again. Keeping the parsing here means the prompt behaviour can be
tested without simulating a keyboard.

This fixes a real hang: the original asked
``[default: full dataset]`` and then rejected an empty answer whenever no
default existed, so pressing Enter looped forever.
"""

from __future__ import annotations

from typing import Sequence

#: Row count above which a sample size is suggested for plotting.
LARGE_DATASET_THRESHOLD = 150_000
#: Sample size suggested for large datasets.
DEFAULT_LARGE_SAMPLE = 50_000


class PromptError(ValueError):
    """The user's answer could not be understood."""


def parse_sample_size(
    text: str,
    row_count: int,
    *,
    large_threshold: int = LARGE_DATASET_THRESHOLD,
    large_default: int = DEFAULT_LARGE_SAMPLE,
) -> int | None:
    """Parse the plot sample-size answer. ``None`` means "use every row".

    An empty answer always means "accept whatever the prompt advertised", so it
    can never leave the caller stuck:

    * large dataset -> ``large_default``
    * otherwise -> ``None`` (the full dataset)
    """
    answer = (text or "").strip().lower()

    if answer == "":
        return large_default if row_count > large_threshold else None
    if answer == "none":
        return None

    try:
        value = int(answer)
    except ValueError as exc:
        raise PromptError("Enter a whole number of rows, or 'none'.") from exc

    if value <= 0:
        raise PromptError("Sample size must be a positive number of rows.")
    return value


def parse_file_selection(text: str, file_count: int) -> list[int]:
    """Parse "1,3" into zero-based indices.

    An empty answer picks the last file (as the prompt says). Anything that
    cannot be parsed raises instead of silently falling back, so a typo never
    processes the wrong dataset. Duplicates are collapsed.
    """
    if file_count <= 0:
        raise PromptError("No files are available to select.")

    answer = (text or "").strip()
    if answer == "":
        return [file_count - 1]

    indices: list[int] = []
    for part in answer.split(","):
        chunk = part.strip()
        if not chunk:
            continue
        try:
            number = int(chunk)
        except ValueError as exc:
            raise PromptError(f"{chunk!r} is not a file number.") from exc
        if not 1 <= number <= file_count:
            raise PromptError(
                f"File number {number} is out of range 1-{file_count}."
            )
        index = number - 1
        if index not in indices:
            indices.append(index)

    if not indices:
        raise PromptError("No file numbers entered.")
    return indices


def parse_column_selection(
    text: str, columns: Sequence[object]
) -> tuple[list[str], list[str]]:
    """Split a comma-separated column answer into ``(valid, unknown)``.

    Unknown names are returned rather than dropped silently, so the caller can
    tell the user which column names were wrong.
    """
    answer = (text or "").strip()
    if not answer or answer.lower() == "none":
        return [], []

    available = {str(column) for column in columns}
    valid: list[str] = []
    unknown: list[str] = []
    for part in answer.split(","):
        name = part.strip()
        if not name:
            continue
        if name in available:
            if name not in valid:
                valid.append(name)
        elif name not in unknown:
            unknown.append(name)
    return valid, unknown
