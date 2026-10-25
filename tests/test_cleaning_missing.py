"""Missing-value handling.

The headline regression here is that filling used to report success while
changing nothing: ``df[col].fillna(..., inplace=True)`` operates on a temporary
Series under copy-on-write.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from data_prep import CleaningOptions, clean_data


def test_fill_numeric_mean_actually_fills():
    df = pd.DataFrame({"amount": [10.0, np.nan, 30.0]})

    cleaned, summary = clean_data(df, CleaningOptions(missing_values="fill"))

    assert cleaned["amount"].tolist() == [10.0, 20.0, 30.0]
    assert not cleaned.isna().any().any()
    assert summary.fills[0].column == "amount"
    assert summary.fills[0].strategy == "mean"
    assert summary.fills[0].value == 20.0
    assert summary.fills[0].count == 1


def test_fill_numeric_median():
    # Median of 10, 20, 30, 100 is 25; the mean would be 40.
    df = pd.DataFrame({"amount": [10.0, np.nan, 20.0, 30.0, 100.0]})

    cleaned, summary = clean_data(
        df, CleaningOptions(missing_values="fill", fill_numeric="median")
    )

    assert cleaned["amount"].tolist() == [10.0, 25.0, 20.0, 30.0, 100.0]
    assert df["amount"].mean() == 40.0  # proves median != mean here
    assert summary.fills[0].strategy == "median"


def test_fill_text_uses_mode():
    df = pd.DataFrame({"city": ["Pune", None, "Pune", "Delhi"]})

    cleaned, _ = clean_data(df, CleaningOptions(missing_values="fill"))

    assert cleaned["city"].tolist() == ["Pune", "Pune", "Pune", "Delhi"]


def test_fill_all_empty_text_column_uses_constant():
    df = pd.DataFrame({"reason": [None, None, None]})

    cleaned, summary = clean_data(df, CleaningOptions(missing_values="fill"))

    assert cleaned["reason"].tolist() == ["Unknown", "Unknown", "Unknown"]
    assert summary.fills[0].strategy == "constant"


def test_fill_custom_constant():
    df = pd.DataFrame({"flag": [None, "y"]})

    cleaned, _ = clean_data(
        df,
        CleaningOptions(
            missing_values="fill", fill_categorical="constant", fill_constant="n/a"
        ),
    )

    assert cleaned["flag"].tolist() == ["n/a", "y"]


def test_fill_nullable_boolean_does_not_crash():
    """Regression: mean (0.5) cannot be stored in a ``boolean`` column.

    Before: ``TypeError: Invalid value '0.5' for dtype 'boolean'``.
    """
    df = pd.DataFrame({"is_active": pd.array([True, False, None], dtype="boolean")})

    cleaned, _ = clean_data(df, CleaningOptions(missing_values="fill"))

    assert cleaned["is_active"].tolist() == [True, False, False]
    assert str(cleaned["is_active"].dtype) == "boolean"


def test_fill_all_empty_datetime_is_left_alone_with_a_warning():
    df = pd.DataFrame({"when": pd.Series([pd.NaT, pd.NaT], dtype="datetime64[ns]")})

    cleaned, summary = clean_data(df, CleaningOptions(missing_values="fill"))

    assert cleaned["when"].isna().all()
    assert any("entirely empty" in warning for warning in summary.warnings)


def test_fill_integer_column_needing_a_fraction_is_reported():
    """An Int64 column cannot hold a fractional mean; we cast and say so."""
    df = pd.DataFrame({"count": pd.array([1, 2, None], dtype="Int64")})

    cleaned, summary = clean_data(df, CleaningOptions(missing_values="fill"))

    assert not cleaned["count"].isna().any()
    assert any("cast to float" in warning for warning in summary.warnings)


def test_fill_warns_when_column_is_mostly_empty():
    """A 94%-missing column filled with a mean invents most of its values."""
    df = pd.DataFrame({"value": [1.0] + [np.nan] * 15})

    _, summary = clean_data(df, CleaningOptions(missing_values="fill"))

    assert any("was 94% missing" in warning for warning in summary.warnings)


def test_drop_missing_values_removes_the_rows():
    df = pd.DataFrame({"a": [1.0, np.nan, 3.0], "b": ["x", "y", None]})

    cleaned, summary = clean_data(df, CleaningOptions(missing_values="drop"))

    assert len(cleaned) == 1
    assert summary.rows_dropped_missing == 2
    assert summary.rows_out == 1


def test_drop_everything_warns_and_reports_zero_rows():
    """Regression: the run then wrote an empty CSV and printed success."""
    df = pd.DataFrame({"a": [1.0, np.nan], "b": [None, None]})

    cleaned, summary = clean_data(df, CleaningOptions(missing_values="drop"))

    assert cleaned.empty
    assert summary.rows_out == 0
    assert any("0 rows" in warning for warning in summary.warnings)
    assert any("Most incomplete columns" in warning for warning in summary.warnings)


def test_missing_values_none_changes_nothing():
    df = pd.DataFrame({"a": [1.0, np.nan]})

    cleaned, summary = clean_data(df, CleaningOptions(missing_values="none"))

    assert cleaned.isna().sum().sum() == 1
    assert summary.fills == []


def test_fill_skips_columns_with_no_missing_values():
    df = pd.DataFrame({"a": [1.0, 2.0], "b": [1.0, np.nan]})

    _, summary = clean_data(df, CleaningOptions(missing_values="fill"))

    assert [fill.column for fill in summary.fills] == ["b"]


def test_cleaning_does_not_mutate_the_input():
    df = pd.DataFrame({"a": [1.0, np.nan]})
    original = df.copy(deep=True)

    clean_data(df, CleaningOptions(missing_values="fill"))

    assert df.equals(original)


def test_invalid_options_are_rejected_early():
    with pytest.raises(ValueError, match="missing_values"):
        CleaningOptions(missing_values="delete")
    with pytest.raises(ValueError, match="numeric_coercion"):
        CleaningOptions(numeric_coercion="aggressive")
    with pytest.raises(ValueError, match="fill_numeric"):
        CleaningOptions(fill_numeric="geometric")
