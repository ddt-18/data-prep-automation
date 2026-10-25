"""Integration test against the real 150k-row dataset used in the README.

The file is not in the working tree (it was deleted), but it is still in git
history, so these tests recover it with ``git show`` and skip cleanly in a
shallow clone or an export without ``.git``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd
import pytest

from data_prep import (
    CleaningOptions,
    EmptyOutputError,
    clean_data,
    identifier_reason,
    load_table,
    save_outputs,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REVISION = "6aa6226"
BLOB_PATH = "Datasets/ncr_ride_bookings.csv"


@pytest.fixture(scope="module")
def bookings(tmp_path_factory) -> pd.DataFrame:
    try:
        result = subprocess.run(
            ["git", "show", f"{REVISION}:{BLOB_PATH}"],
            cwd=REPO_ROOT,
            capture_output=True,
            timeout=180,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        pytest.skip(f"git is unavailable: {exc}")
    if result.returncode != 0:  # pragma: no cover - shallow clones
        pytest.skip("dataset blob is not reachable in this clone")

    target = tmp_path_factory.mktemp("real") / "ncr_ride_bookings.csv"
    target.write_bytes(result.stdout)
    return load_table(target)


def test_shape_matches_the_readme(bookings):
    assert bookings.shape == (150_000, 21)


def test_identifiers_are_quote_wrapped(bookings):
    """The stored values really are '"CNR5884300"', quotes included."""
    assert bookings["Booking ID"].astype(str).str.startswith('"').all()
    assert "identifier" in (identifier_reason("Booking ID", bookings["Booking ID"]) or "")


def test_identifiers_are_never_converted_to_numbers(bookings):
    cleaned, summary = clean_data(bookings, CleaningOptions(numeric_coercion="safe"))

    assert cleaned["Booking_ID"].astype(str).str.startswith('"').all()
    assert summary.coercions  # safe mode ran and recorded its decisions
    reasons = {record.column: record.reason for record in summary.coercions}
    assert "identifier" in reasons["Booking_ID"]


def test_all_column_dedupe_finds_nothing(bookings):
    """Documents the trap: rows differ, so whole-row dedupe removes 0 rows."""
    _, summary = clean_data(bookings, CleaningOptions(drop_duplicates=True))

    assert summary.duplicates_removed == 0
    assert any("duplicate_subset" in warning for warning in summary.warnings)


def test_keyed_dedupe_finds_the_1233_repeated_ids(bookings):
    cleaned, summary = clean_data(
        bookings,
        CleaningOptions(drop_duplicates=True, duplicate_subset=["Booking ID"]),
    )

    assert summary.duplicates_removed == 1233
    assert len(cleaned) == 148_767
    assert cleaned["Booking_ID"].is_unique


def test_dropping_missing_values_would_delete_every_row(bookings):
    """Every row has at least one null, so global dropna yields 0 rows."""
    cleaned, summary = clean_data(bookings, CleaningOptions(missing_values="drop"))

    assert len(cleaned) == 0
    assert summary.rows_dropped_missing == 150_000
    assert any("0 rows" in warning for warning in summary.warnings)


def test_empty_result_is_not_written(bookings, tmp_path):
    cleaned, _ = clean_data(bookings, CleaningOptions(missing_values="drop"))

    with pytest.raises(EmptyOutputError):
        save_outputs(cleaned, "ncr_ride_bookings", tmp_path)


def test_mean_filling_invents_booking_values(bookings):
    """32% of Booking Value is missing - every one on a ride that never happened.

    The fill is legitimate when asked for, but the summary must record how much
    was invented so the choice is visible.
    """
    cleaned, summary = clean_data(bookings, CleaningOptions(missing_values="fill"))

    filled = {record.column: record for record in summary.fills}
    assert filled["Booking_Value"].count == 48_000
    assert filled["Booking_Value"].strategy == "mean"
    assert not cleaned["Booking_Value"].isna().any()


def test_mostly_empty_columns_are_flagged(bookings):
    _, summary = clean_data(bookings, CleaningOptions(missing_values="fill"))

    assert any("94% missing" in warning for warning in summary.warnings)
