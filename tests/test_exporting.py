"""Writing outputs: empty-data refusal and the Excel row limit."""

from __future__ import annotations

import pandas as pd
import pytest

from data_prep import EmptyOutputError, save_outputs


def test_empty_dataframe_is_refused(tmp_path):
    """Regression: an empty cleaned file was written and reported as success."""
    empty = pd.DataFrame({"a": pd.Series([], dtype="float64")})

    with pytest.raises(EmptyOutputError, match="allow_empty=True"):
        save_outputs(empty, "bookings", tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_empty_dataframe_can_be_written_on_request(tmp_path):
    empty = pd.DataFrame({"a": pd.Series([], dtype="float64")})

    paths = save_outputs(empty, "bookings", tmp_path, allow_empty=True)

    assert paths.csv.exists()
    assert paths.csv.read_text().strip() == "a"


def test_csv_and_excel_are_written(tmp_path):
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})

    paths = save_outputs(df, "bookings", tmp_path, timestamp="20260101_120000")

    assert paths.csv == tmp_path / "bookings_cleaned_20260101_120000.csv"
    assert paths.excel == tmp_path / "bookings_cleaned_20260101_120000.xlsx"
    assert paths.csv.exists() and paths.excel.exists()
    assert paths.notes == []


def test_leading_zeros_survive_the_csv_roundtrip(tmp_path):
    df = pd.DataFrame({"zip": ["01234", "00567"]})

    paths = save_outputs(df, "zips", tmp_path, timestamp="t")

    reloaded = pd.read_csv(paths.csv, dtype=str)
    assert reloaded["zip"].tolist() == ["01234", "00567"]


def test_excel_is_skipped_when_the_sheet_would_overflow(tmp_path):
    """The header row counts toward Excel's limit, so the check is rows + 1."""
    df = pd.DataFrame({"a": [1, 2, 3]})

    paths = save_outputs(df, "x", tmp_path, timestamp="t", excel_row_limit=3)

    assert paths.csv.exists()
    assert paths.excel is None
    assert any("exceeds Excel" in note for note in paths.notes)


def test_excel_is_written_exactly_at_the_limit(tmp_path):
    df = pd.DataFrame({"a": [1, 2, 3]})

    paths = save_outputs(df, "x", tmp_path, timestamp="t", excel_row_limit=4)

    assert paths.excel is not None and paths.excel.exists()


def test_excel_can_be_disabled(tmp_path):
    df = pd.DataFrame({"a": [1]})

    paths = save_outputs(df, "x", tmp_path, timestamp="t", write_excel=False)

    assert paths.excel is None
    assert "Excel export disabled" in paths.notes


def test_unsafe_base_filename_stays_inside_the_output_folder(tmp_path):
    df = pd.DataFrame({"a": [1]})

    paths = save_outputs(df, "../../evil", tmp_path, timestamp="t")

    assert paths.csv.parent == tmp_path
    assert paths.csv.name.startswith("evil")


def test_output_folder_is_created(tmp_path):
    df = pd.DataFrame({"a": [1]})
    nested = tmp_path / "output" / "run1"

    paths = save_outputs(df, "x", nested, timestamp="t")

    assert paths.csv.exists()


def test_unsafe_characters_in_base_filename_are_made_safe(tmp_path):
    df = pd.DataFrame({"a": [1]})

    first = save_outputs(df, "sales.csv", tmp_path, timestamp="t")
    second = save_outputs(df, "sales.json", tmp_path, timestamp="t")

    assert first.csv.name.startswith("sales_csv")
    assert second.csv.name.startswith("sales_json")
    assert first.csv != second.csv
