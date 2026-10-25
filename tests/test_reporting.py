"""HTML report generation (requires the optional ydata-profiling dependency)."""

from __future__ import annotations

import pandas as pd
import pytest

from data_prep import EmptyOutputError, build_report

pytest.importorskip("ydata_profiling", reason="ydata-profiling not installed")


def test_report_is_written(tmp_path):
    df = pd.DataFrame({"city": ["Pune", "Delhi"], "amount": [10, 20]})

    path = build_report(df, "bookings", tmp_path, date_stamp="20260101")

    assert path == tmp_path / "bookings_report_20260101.html"
    assert path.exists()
    assert path.stat().st_size > 1000


def test_empty_frame_is_refused(tmp_path):
    df = pd.DataFrame({"a": pd.Series([], dtype="float64")})

    with pytest.raises(EmptyOutputError):
        build_report(df, "bookings", tmp_path)


def test_report_filename_is_safe(tmp_path):
    df = pd.DataFrame({"a": [1, 2]})

    path = build_report(df, "../../escape", tmp_path, date_stamp="20260101")

    assert path.parent == tmp_path
    assert path.name.startswith("escape_report")
