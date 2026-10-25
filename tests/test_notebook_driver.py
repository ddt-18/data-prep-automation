"""End-to-end test of the notebook, driven with simulated keystrokes.

This is the test that would have caught the infinite sample-size prompt: it runs
the notebook's own code cells the way a beginner would, by answering the
questions, then checks that the expected files appear.
"""

from __future__ import annotations

import builtins
import json
from pathlib import Path

import pandas as pd
import pytest

NOTEBOOK = Path(__file__).resolve().parents[1] / "data_preprocessing_automation.ipynb"


def _code_cells() -> list[str]:
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    return [
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    ]


class Driver:
    """Feeds scripted answers to ``input()`` and reports when they run out."""

    def __init__(self, answers: list[str]) -> None:
        self.answers = list(answers)
        self.prompts: list[str] = []

    def __call__(self, prompt: str = "") -> str:
        self.prompts.append(prompt)
        if not self.answers:
            raise AssertionError(
                "The notebook asked more questions than expected. "
                f"Last prompt: {prompt!r}"
            )
        return self.answers.pop(0)


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """A folder with one small CSV and a cwd the notebook can use."""
    (tmp_path / "src").symlink_to(Path(__file__).resolve().parents[1] / "src")
    (
        tmp_path
        / "bookings.csv"
    ).write_text(
        "Booking ID,City,Status,Booking Value\n"
        "CNR1,Pune,Completed,100\n"
        "CNR1,Pune,Cancelled by Driver,\n"
        "CNR2,Delhi,Completed,300\n"
        "CNR3,Mumbai,Incomplete,\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run_notebook(answers: list[str]):
    driver = Driver(answers)
    original_input = builtins.input
    builtins.input = driver
    namespace: dict[str, object] = {"__name__": "__main__"}
    try:
        for source in _code_cells():
            exec(compile(source, "<notebook>", "exec"), namespace)
    finally:
        builtins.input = original_input
    return namespace, driver


def test_notebook_runs_end_to_end(workspace):
    """Press Enter everywhere: folder default, keyed dedupe, full dataset."""
    answers = [
        "",          # dataset folder: default = current directory
        "",          # file selection: default = last (the only one)
        "2",         # missing values: fill
        "y",         # drop duplicates
        "Booking ID",  # duplicate key
        "",          # convert text to numbers: default n
        "n",         # pick chart columns manually? no
        "",          # sample size: default (full dataset, no hang)
    ]
    namespace, driver = run_notebook(answers)

    output = workspace / "output"
    csv_files = list(output.glob("bookings_cleaned_*.csv"))
    assert len(csv_files) == 1, f"no cleaned CSV; prompts were {driver.prompts}"

    cleaned = pd.read_csv(csv_files[0], dtype=str)
    assert cleaned["Booking_ID"].tolist() == ["CNR1", "CNR2", "CNR3"]
    # Text was never converted to numbers, so every value is still a string.
    assert cleaned["Booking_Value"].tolist() == ["100.0", "300.0", "200.0"]
    assert sorted(path.name for path in (output / "bookings_plots").glob("*.png"))
    assert list(output.glob("processing_*.log"))


def test_notebook_keeps_all_rows_when_asked(workspace):
    """With 'do nothing' and whole-row dedupe, nothing is removed."""
    answers = ["", "", "3", "n", "", "n", ""]
    namespace, _ = run_notebook(answers)

    cleaned_files = list((workspace / "output").glob("bookings_cleaned_*.csv"))
    cleaned = pd.read_csv(cleaned_files[0], dtype=str)
    assert len(cleaned) == 4


def test_notebook_reports_a_bad_choice_and_asks_again(workspace):
    answers = ["", "", "9", "abc", "3", "maybe", "n", "", "n", ""]
    _, driver = run_notebook(answers)

    assert any("Invalid choice" in prompt or prompt for prompt in driver.prompts)
    assert len(driver.prompts) == 10


def test_notebook_does_not_hang_on_a_long_prompt_cycle(workspace):
    """Guards the original bug: an empty sample size must never re-prompt."""
    answers = ["", "", "3", "n", "", "n", ""]
    run_notebook(answers)  # would raise AssertionError if prompts ran out
