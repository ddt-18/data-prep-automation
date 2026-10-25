"""Type conversion: text is never turned into numbers by accident.

The original ran ``pd.to_numeric(errors="ignore")`` over every column, so
``"01234"`` became ``1234`` and ``"007"`` became ``7``. The agreed policy is
strict: no automatic coercion, and even the opt-in ``"safe"`` mode protects
identifier-like columns.
"""

from __future__ import annotations

import pandas as pd
import pytest

from data_prep import CleaningOptions, clean_data, identifier_reason


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (["01234", "00567"], ["01234", "00567"]),        # ZIP codes
        (["007", "008"], ["007", "008"]),                # product codes
        (["123", "456"], ["123", "456"]),                # plain text numbers
        (["1,234", "5,678"], ["1,234", "5,678"]),        # thousands separators
    ],
)
def test_default_keeps_text_exactly_as_it_was(values, expected):
    df = pd.DataFrame({"code": values})

    cleaned, summary = clean_data(df)

    assert cleaned["code"].tolist() == expected
    assert summary.coercions == []


def test_default_does_not_touch_quoted_identifiers():
    df = pd.DataFrame({"Booking ID": ['"CNR5884300"', '"CNR1326809"']})

    cleaned, _ = clean_data(df)

    assert cleaned["Booking_ID"].tolist() == ['"CNR5884300"', '"CNR1326809"']


def test_safe_mode_converts_genuinely_numeric_text():
    df = pd.DataFrame({"amount": ["10", "20", "30"]})

    cleaned, summary = clean_data(df, CleaningOptions(numeric_coercion="safe"))

    assert pd.api.types.is_numeric_dtype(cleaned["amount"])
    assert cleaned["amount"].tolist() == [10, 20, 30]
    assert summary.coercions[0].converted is True


def test_safe_mode_skips_columns_whose_name_is_an_identifier():
    df = pd.DataFrame({"customer_id": ["1", "2"], "zip": ["01234", "00567"]})

    cleaned, summary = clean_data(df, CleaningOptions(numeric_coercion="safe"))

    assert cleaned["customer_id"].tolist() == ["1", "2"]
    reasons = {record.column: record.reason for record in summary.coercions}
    assert "identifier" in reasons["customer_id"]
    assert "identifier" in reasons["zip"]  # the name alone is enough to protect it


def test_safe_mode_skips_by_values_even_without_an_identifier_name():
    df = pd.DataFrame({"value": ["01234", "00567", "00090"]})

    cleaned, summary = clean_data(df, CleaningOptions(numeric_coercion="safe"))

    assert cleaned["value"].tolist() == ["01234", "00567", "00090"]
    assert summary.coercions[0].converted is False
    assert "leading zeros" in summary.coercions[0].reason


def test_safe_mode_keeps_mixed_columns_as_text():
    df = pd.DataFrame({"amount": ["10", "twenty"]})

    cleaned, summary = clean_data(df, CleaningOptions(numeric_coercion="safe"))

    assert cleaned["amount"].tolist() == ["10", "twenty"]
    assert summary.coercions[0].converted is False
    assert "not numeric" in summary.coercions[0].reason


def test_safe_mode_does_not_convert_long_digit_strings():
    df = pd.DataFrame({"tracking": ["123456789012345", "999888777666555"]})

    _, summary = clean_data(df, CleaningOptions(numeric_coercion="safe"))

    assert summary.coercions[0].converted is False
    assert "long digit" in summary.coercions[0].reason


def test_safe_mode_never_loses_values():
    """Whatever happens, no cell may turn into NaN through conversion."""
    df = pd.DataFrame({"values": ["1", "2", None, "x"]})

    cleaned, _ = clean_data(df, CleaningOptions(numeric_coercion="safe"))

    assert cleaned["values"].isna().sum() == 1


@pytest.mark.parametrize(
    "name",
    ["paid", "valid", "width", "avoid", "booking_status", "Paid Amount"],
)
def test_words_containing_id_are_not_identifiers(name):
    """The old substring match excluded any column containing "id"."""
    series = pd.Series(["1", "2"])
    assert identifier_reason(name, series) is None


@pytest.mark.parametrize(
    "name",
    ["id", "Booking ID", "customer_id", "VendorID", "zip_code", "phone_number", "RideId"],
)
def test_identifier_names_are_detected(name):
    series = pd.Series(["1", "2"])
    reason = identifier_reason(name, series)
    assert reason is not None and "identifier" in reason


def test_identifier_detection_ignores_numeric_columns():
    """A numeric column called ``id`` is already numeric; nothing to protect."""
    assert identifier_reason("id", pd.Series([1, 2, 3])) is not None  # name wins
    assert identifier_reason("amount", pd.Series([1.5, 2.5])) is None
