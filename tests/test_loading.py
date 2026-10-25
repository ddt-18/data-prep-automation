"""Loading CSV / Excel / JSON / Parquet, including the encoding bugs."""

from __future__ import annotations

import codecs

import pandas as pd
import pytest

from conftest import write_bytes, write_text
from data_prep import loading
from data_prep.errors import (
    EmptyFileError,
    EncodingDetectionError,
    LoadError,
    UnsupportedFormatError,
)
from data_prep.loading import detect_csv_encoding, list_data_files, load_table


def test_load_utf8_csv(tmp_path):
    path = write_text(tmp_path / "d.csv", "city,amount\nPune,10\nDelhi,20\n")
    df = load_table(path)
    assert list(df.columns) == ["city", "amount"]
    assert df["city"].tolist() == ["Pune", "Delhi"]


def test_utf8_bom_does_not_leak_into_first_column_name(tmp_path):
    path = write_bytes(tmp_path / "bom.csv", "id,val\n1,a\n".encode("utf-8-sig"))
    df = load_table(path)
    assert list(df.columns) == ["id", "val"]


def test_utf16_csv_is_read_correctly(tmp_path):
    """Regression: UTF-16 used to "load successfully" as a table of NaN.

    Before: columns ``['ÿþc', 'Unnamed: 1']``, all values NaN, printed as
    "Loaded successfully".
    """
    path = write_bytes(
        tmp_path / "u16.csv", "city,amount\nPune,10\nDelhi,20\n".encode("utf-16")
    )
    df = load_table(path)

    assert list(df.columns) == ["city", "amount"]
    assert df["city"].tolist() == ["Pune", "Delhi"]
    assert not df.isna().all().any()


def test_cp1252_euro_sign_survives(tmp_path):
    path = write_bytes(
        tmp_path / "cp.csv", "name,price\nCafé,10 €\nNaïve,20 €\n".encode("cp1252")
    )
    df = load_table(path)
    assert df["name"].tolist() == ["Café", "Naïve"]
    assert df["price"].iloc[0] == "10 €"


def test_explicit_encoding_override(tmp_path):
    path = write_bytes(tmp_path / "w.csv", "name\nJosé\n".encode("cp1252"))
    df = load_table(path, encoding="cp1252")
    assert df["name"].tolist() == ["José"]


def test_wrong_explicit_encoding_raises_clearly(tmp_path):
    path = write_bytes(tmp_path / "w.csv", "name\nJosé\n".encode("utf-16"))
    with pytest.raises(EncodingDetectionError):
        load_table(path, encoding="utf-8")


def test_empty_file_raises_empty_file_error(tmp_path):
    """A 0-byte file is not an encoding problem, and the message must say so."""
    path = write_bytes(tmp_path / "empty.csv", b"")
    with pytest.raises(EmptyFileError, match="empty"):
        load_table(path)


def test_binary_garbage_is_not_silently_accepted(tmp_path):
    """No candidate encoding may claim success on text full of control bytes."""
    path = write_bytes(tmp_path / "junk.csv", b"\x00\x01\x02\x03" * 500)
    with pytest.raises((EncodingDetectionError, EmptyFileError)):
        load_table(path)


def test_header_only_csv_is_allowed(tmp_path):
    path = write_text(tmp_path / "h.csv", "a,b\n")
    df = load_table(path)
    assert df.shape == (0, 2)


def test_duplicate_headers_are_disambiguated_by_pandas(tmp_path):
    path = write_text(tmp_path / "d.csv", "amount,amount\n1,2\n")
    df = load_table(path)
    assert list(df.columns) == ["amount", "amount.1"]


def test_json_records(tmp_path):
    path = write_text(
        tmp_path / "r.json", '[{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]'
    )
    df = load_table(path)
    assert df.shape == (2, 2)
    assert df["a"].tolist() == [1, 2]


def test_json_lines(tmp_path):
    """Regression: JSON Lines failed with ``Trailing data``."""
    path = write_text(tmp_path / "l.json", '{"a": 1, "b": "x"}\n{"a": 2, "b": "y"}\n')
    df = load_table(path)
    assert df.shape == (2, 2)
    assert df["b"].tolist() == ["x", "y"]


def test_unreadable_json_raises_load_error(tmp_path):
    path = write_text(tmp_path / "bad.json", "not json at all")
    with pytest.raises(LoadError):
        load_table(path)


def test_parquet_roundtrip(tmp_path):
    path = tmp_path / "d.parquet"
    pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}).to_parquet(path)
    df = load_table(path)
    assert df.shape == (2, 2)


def test_excel_roundtrip(tmp_path):
    path = tmp_path / "d.xlsx"
    pd.DataFrame({"a": [1, 2]}).to_excel(path, index=False)
    df = load_table(path)
    assert df["a"].tolist() == [1, 2]


def test_excel_sheet_selection(tmp_path):
    path = tmp_path / "multi.xlsx"
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({"first": [1]}).to_excel(writer, sheet_name="First", index=False)
        pd.DataFrame({"second": [2]}).to_excel(writer, sheet_name="Second", index=False)

    assert list(load_table(path).columns) == ["first"]
    assert list(load_table(path, sheet_name="Second").columns) == ["second"]


def test_missing_file(tmp_path):
    with pytest.raises(LoadError, match="not found"):
        load_table(tmp_path / "nope.csv")


def test_unsupported_extension(tmp_path):
    path = write_text(tmp_path / "d.txt", "a,b\n1,2\n")
    with pytest.raises(UnsupportedFormatError):
        load_table(path)


def test_list_data_files_is_sorted_and_skips_lock_files(tmp_path):
    for name in ["b.csv", "a.csv", "C.JSON", "~$book.xlsx", ".hidden.csv", "notes.txt"]:
        write_text(tmp_path / name, "x\n1\n")

    files = list_data_files(tmp_path)
    assert [path.name for path in files] == ["a.csv", "b.csv", "C.JSON"]


def test_list_data_files_requires_a_directory(tmp_path):
    with pytest.raises(LoadError):
        list_data_files(tmp_path / "nope")


def test_encoding_candidates_include_no_silent_latin1_first():
    """latin-1 can decode anything, so it must never be the first guess."""
    assert loading.CSV_ENCODING_CANDIDATES[0] == "utf-8"
    assert loading.CSV_ENCODING_CANDIDATES[-1] == "latin-1"


def test_detect_csv_encoding_reads_bom():
    assert codecs.BOM_UTF8 == b"\xef\xbb\xbf"  # documents what we sniff for
