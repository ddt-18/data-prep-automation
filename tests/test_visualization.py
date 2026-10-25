"""Charts: filenames, auto-selection and the shapes we refuse to draw."""

from __future__ import annotations

import pandas as pd
import pytest

from data_prep.visualization import (
    auto_select_columns,
    categorical_columns,
    excluded_column,
    make_charts,
    select_plot_frame,
)


@pytest.fixture
def chart_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "City": ["Pune", "Mumbai", "Pune", "Delhi", "Mumbai", "Pune"],
            "Status": ["ok", "bad", "ok", "ok", "bad", "ok"],
            "paid": ["y", "n", "y", "y", "n", "y"],
            "amount": [1, 2, 3, 4, 5, 6],
        }
    )


def test_bar_chart_is_written(tmp_path, chart_frame):
    paths, notes = make_charts(
        chart_frame, "bookings", tmp_path, bar_columns=["City"]
    )

    assert [path.name for path in paths] == ["bar_City.png"]
    assert paths[0].exists() and paths[0].stat().st_size > 1000
    assert notes == []


def test_pie_chart_is_written(tmp_path, chart_frame):
    paths, _ = make_charts(chart_frame, "bookings", tmp_path, pie_columns=["Status"])

    assert [path.name for path in paths] == ["pie_Status.png"]
    assert paths[0].exists()


def test_column_name_with_a_slash_does_not_crash(tmp_path, chart_frame):
    """Regression: ``FileNotFoundError: .../bar_a/b.png``."""
    frame = chart_frame.rename(columns={"City": "a/b"})

    paths, _ = make_charts(frame, "bookings", tmp_path, bar_columns=["a/b"])

    assert [path.name for path in paths] == ["bar_a_b.png"]
    assert paths[0].parent.name == "bookings_plots"


def test_traversal_style_column_name_cannot_escape(tmp_path, chart_frame):
    frame = chart_frame.rename(columns={"City": "../../escaped"})

    paths, _ = make_charts(frame, "bookings", tmp_path, bar_columns=["../../escaped"])

    assert paths[0].parent == tmp_path / "bookings_plots"
    assert ".." not in str(paths[0])


def test_two_columns_with_similar_slugs_do_not_overwrite(tmp_path, chart_frame):
    frame = chart_frame.rename(columns={"City": "a/b", "Status": "a:b"})

    paths, _ = make_charts(frame, "bookings", tmp_path, bar_columns=["a/b", "a:b"])

    assert len(paths) == 2
    assert len({path.name for path in paths}) == 2


def test_pie_needs_between_two_and_ten_slices(tmp_path):
    frame = pd.DataFrame({"single": ["x", "x", "x"]})

    paths, notes = make_charts(frame, "x", tmp_path, pie_columns=["single"])

    assert paths == []
    assert any("pie chart skipped" in note for note in notes)


def test_unknown_column_is_reported_not_raised(tmp_path, chart_frame):
    paths, notes = make_charts(chart_frame, "x", tmp_path, bar_columns=["nope"])

    assert paths == []
    assert any("no column named" in note for note in notes)


def test_all_empty_column_is_skipped(tmp_path):
    frame = pd.DataFrame({"empty": [None, None]})

    paths, notes = make_charts(frame, "x", tmp_path, bar_columns=["empty"])

    assert paths == []
    assert any("no values" in note for note in notes)


def test_empty_frame_produces_a_note_not_a_crash(tmp_path):
    frame = pd.DataFrame({"a": pd.Series([], dtype="object")})

    paths, notes = make_charts(frame, "x", tmp_path, bar_columns=["a"])

    assert paths == []
    assert notes == ["no rows available for charts"]


@pytest.mark.parametrize("name", ["paid", "valid", "width", "avoid", "Paid Amount"])
def test_words_containing_id_are_not_excluded(name):
    """The old substring match excluded any column containing "id"."""
    assert excluded_column(name) is False


@pytest.mark.parametrize(
    "name", ["Booking ID", "customer_id", "VendorID", "phone_number", "Driver Name"]
)
def test_identifier_and_text_columns_are_excluded(name):
    assert excluded_column(name) is True


def test_auto_selection_avoids_identifiers(chart_frame):
    frame = chart_frame.assign(**{"Booking ID": [f"CNR{i}" for i in range(6)]})

    bar_columns, pie_columns = auto_select_columns(frame)

    assert "Booking ID" not in bar_columns + pie_columns
    assert "Status" in pie_columns


def test_categorical_columns_works_with_pandas3_string_dtype():
    frame = pd.DataFrame({"text": pd.Series(["a", "b"], dtype="string")})
    assert "text" in categorical_columns(frame)


def test_sampling_returns_the_requested_number_of_rows(chart_frame):
    frame, sampled = select_plot_frame(chart_frame, sample_size=3)

    assert sampled is True
    assert len(frame) == 3


def test_sampling_is_ignored_when_it_would_not_shrink_the_frame(chart_frame):
    frame, sampled = select_plot_frame(chart_frame, sample_size=1000)

    assert sampled is False
    assert len(frame) == len(chart_frame)


def test_plots_folder_uses_a_safe_name(tmp_path, chart_frame):
    paths, _ = make_charts(chart_frame, "my/data", tmp_path, bar_columns=["City"])

    assert paths[0].parent.name == "my_data_plots"


def test_charts_auto_select_when_nothing_is_chosen(tmp_path, chart_frame):
    """Regression guard: declining manual selection used to produce no charts."""
    paths, notes = make_charts(chart_frame, "bookings", tmp_path)

    assert paths, "auto-selection produced no charts"
    assert any("auto-selected" in note for note in notes)


def test_notes_when_there_is_nothing_categorical_to_plot(tmp_path):
    frame = pd.DataFrame({"amount": [1.0, 2.0], "Booking ID": ["a", "b"]})

    paths, notes = make_charts(frame, "x", tmp_path)

    assert paths == []
    assert any("no suitable categorical columns" in note for note in notes)


def test_same_column_charted_twice_keeps_documented_filenames(tmp_path, chart_frame):
    """bar_X.png and pie_X.png must not become pie_X_2.png."""
    paths, _ = make_charts(
        chart_frame, "bookings", tmp_path, bar_columns=["Status"], pie_columns=["Status"]
    )

    assert sorted(path.name for path in paths) == ["bar_Status.png", "pie_Status.png"]


def test_two_columns_that_slugify_the_same_still_get_unique_names(tmp_path, chart_frame):
    frame = chart_frame.rename(columns={"City": "a/b", "Status": "a:b"})

    paths, _ = make_charts(frame, "bookings", tmp_path, pie_columns=["a/b", "a:b"])

    assert len(set(path.name for path in paths)) == 2
