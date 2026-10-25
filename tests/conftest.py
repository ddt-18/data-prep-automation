"""Shared helpers for the test suite."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # never try to open a window in tests

import pandas as pd
import pytest


@pytest.fixture
def simple_frame() -> pd.DataFrame:
    """Six rows, one numeric column, two text columns."""
    return pd.DataFrame(
        {
            "City": ["Pune", "Mumbai", "Pune", "Delhi", "Mumbai", "Pune"],
            "Status": ["ok", "bad", "ok", "ok", "bad", "ok"],
            "amount": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
        }
    )


@pytest.fixture
def duplicate_id_frame() -> pd.DataFrame:
    """Same Booking ID twice, with different details (the real-dataset trap)."""
    return pd.DataFrame(
        {
            "Booking ID": ["CNR1", "CNR1", "CNR2", "CNR3"],
            "Booking Status": ["Completed", "Cancelled by Driver", "Completed", "Incomplete"],
            "Booking Value": [100.0, None, 300.0, 400.0],
        }
    )


def write_bytes(path, payload: bytes):
    """Write raw bytes to ``path`` (for encoding tests)."""
    path.write_bytes(payload)
    return path


def write_text(path, text: str, encoding: str = "utf-8"):
    """Write text with a specific encoding."""
    path.write_bytes(text.encode(encoding))
    return path
