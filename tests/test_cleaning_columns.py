"""Column renaming and collisions inside ``clean_data``."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from data_prep import CleaningOptions, clean_data


def test_colliding_columns_are_made_unique():
    """Regression: ``Total Price`` + ``Total_Price`` both became ``Total_Price``.

    That produced a DataFrame where downstream ``df[col]`` returned a frame
    instead of a Series, crashing the charts and the profiler with
    ``ValueError: Grouper for 'Total_Price' not 1-dimensional``.
    """
    df = pd.DataFrame({"Total Price": [1, 2], "Total_Price": [3, 4]})

    cleaned, summary = clean_data(df)

    assert list(cleaned.columns) == ["Total_Price", "Total_Price_2"]
    assert not cleaned.columns.duplicated().any()
    assert summary.collisions == ["Total_Price"]
    assert any("both named" in warning for warning in summary.warnings)


def test_renames_are_recorded_with_dtypes():
    df = pd.DataFrame({"Booking ID": ["a", "b"], "Booking Value": [1, 2]})

    _, summary = clean_data(df)

    renames = {rename.original: rename for rename in summary.renames}
    assert renames["Booking ID"].cleaned == "Booking_ID"
    assert renames["Booking Value"].dtype_before == renames["Booking Value"].dtype_after
    assert summary.renamed_columns == {
        "Booking ID": "Booking_ID",
        "Booking Value": "Booking_Value",
    }


def test_non_string_column_labels_do_not_crash():
    """Regression: ``AttributeError: 'int' object has no attribute 'strip'``."""
    df = pd.DataFrame({2023: [1, 2], 2024: [3, 4]})

    cleaned, summary = clean_data(df)

    assert list(cleaned.columns) == ["2023", "2024"]
    assert len(summary.renames) == 2


def test_repeated_whitespace_becomes_one_underscore():
    df = pd.DataFrame({"A  B": [1]})
    cleaned, _ = clean_data(df)
    assert list(cleaned.columns) == ["A_B"]


def test_counts_are_reported():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

    _, summary = clean_data(df)

    assert summary.rows_in == 3
    assert summary.rows_out == 3
    assert summary.columns_in == 2
    assert summary.columns_out == 2


def test_null_counts_use_cleaned_names():
    df = pd.DataFrame({"Booking ID": ["a", None]})

    _, summary = clean_data(df)

    assert summary.null_counts == {"Booking_ID": 1}


def test_summary_is_json_serialisable():
    """Future work turns this summary into a JSON data-quality report."""
    df = pd.DataFrame({"Total Price": [1.0, None], "Total_Price": ["x", "y"]})

    _, summary = clean_data(
        df, CleaningOptions(missing_values="fill", drop_duplicates=True)
    )

    payload = json.dumps(summary.to_dict())
    restored = json.loads(payload)

    assert restored["rows_in"] == 2
    assert restored["columns_out"] == 2
    assert restored["collisions"] == ["Total_Price"]


def test_summary_to_lines_is_readable():
    df = pd.DataFrame({"a": [1.0, None]})

    _, summary = clean_data(df, CleaningOptions(missing_values="fill"))
    lines = summary.to_lines()

    assert any(line.startswith("rows: 2 -> 2") for line in lines)
    assert any("filled a" in line for line in lines)


@pytest.mark.parametrize("column", ["a/b", "a:b", "a*b", "a?b", 'a"b'])
def test_column_names_safe_for_filenames(column):
    df = pd.DataFrame({column: [1, 2]})
    cleaned, _ = clean_data(df)
    assert "/" not in cleaned.columns[0]
    assert cleaned.columns[0]
