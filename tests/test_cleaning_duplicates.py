"""Duplicate removal, including keyed deduplication."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from data_prep import CleaningOptions, clean_data


def test_exact_duplicate_rows_are_removed():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})

    cleaned, summary = clean_data(df, CleaningOptions(drop_duplicates=True))

    assert len(cleaned) == 2
    assert summary.duplicates_removed == 1


def test_identical_row_dedupe_finds_nothing_when_rows_differ(duplicate_id_frame):
    """Documents the trap that made the real dataset report "0 duplicates".

    The same Booking ID appears twice with different details, so comparing every
    column removes nothing - while the duplicates an analyst cares about remain.
    """
    cleaned, summary = clean_data(
        duplicate_id_frame, CleaningOptions(drop_duplicates=True)
    )

    assert summary.duplicates_removed == 0
    assert len(cleaned) == 4
    assert any("duplicate_subset" in warning for warning in summary.warnings)


def test_keyed_dedupe_removes_repeated_ids(duplicate_id_frame):
    cleaned, summary = clean_data(
        duplicate_id_frame,
        CleaningOptions(drop_duplicates=True, duplicate_subset=["Booking ID"]),
    )

    assert summary.duplicates_removed == 1
    assert cleaned["Booking_ID"].tolist() == ["CNR1", "CNR2", "CNR3"]
    # keep='first' keeps the Completed row, not the cancelled one.
    assert cleaned["Booking_Status"].iloc[0] == "Completed"


def test_keyed_dedupe_keep_last(duplicate_id_frame):
    cleaned, _ = clean_data(
        duplicate_id_frame,
        CleaningOptions(
            drop_duplicates=True, duplicate_subset=["Booking ID"], duplicate_keep="last"
        ),
    )

    assert cleaned["Booking_Status"].iloc[0] == "Cancelled by Driver"


def test_subset_accepts_original_column_names():
    """``Booking  ID`` becomes ``Booking_ID``, but either spelling is accepted."""
    df = pd.DataFrame({"Booking  ID": ["a", "a"], "v": [1, 2]})

    cleaned, summary = clean_data(
        df, CleaningOptions(drop_duplicates=True, duplicate_subset=["Booking  ID"])
    )

    assert len(cleaned) == 1
    assert summary.duplicate_subset == ["Booking_ID"]


def test_unknown_subset_column_raises_with_helpful_message():
    df = pd.DataFrame({"a": [1, 2]})

    with pytest.raises(ValueError, match="not in the dataset"):
        clean_data(df, CleaningOptions(drop_duplicates=True, duplicate_subset=["nope"]))


def test_duplicates_removed_before_filling():
    """Dedupe runs on the values as they were, so filling cannot create twins."""
    df = pd.DataFrame({"a": [1.0, np.nan, 2.0], "b": [np.nan, 1.0, 1.0]})

    cleaned, summary = clean_data(
        df, CleaningOptions(drop_duplicates=True, missing_values="fill")
    )

    assert summary.duplicates_removed == 0
    assert not cleaned.isna().any().any()


def test_index_is_reset_after_dropping():
    df = pd.DataFrame({"a": [1, 1, 2]})

    cleaned, _ = clean_data(df, CleaningOptions(drop_duplicates=True))

    assert list(cleaned.index) == [0, 1]


def test_dedupe_off_by_default():
    df = pd.DataFrame({"a": [1, 1]})

    cleaned, summary = clean_data(df)

    assert len(cleaned) == 2
    assert summary.duplicates_removed == 0
