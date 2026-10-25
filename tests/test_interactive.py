"""Prompt parsing - the logic behind the interactive questions."""

from __future__ import annotations

import pytest

from data_prep.interactive import (
    DEFAULT_LARGE_SAMPLE,
    PromptError,
    parse_column_selection,
    parse_file_selection,
    parse_sample_size,
)


def test_enter_accepts_full_dataset_for_small_files():
    """Regression: this exact case looped forever.

    The prompt said ``[default: full dataset]``, but an empty answer was only
    accepted when a numeric default existed, so Enter re-prompted endlessly.
    """
    assert parse_sample_size("", row_count=100) is None


def test_enter_does_not_hang_on_the_readme_example():
    """The README's example has exactly 150,000 rows and the threshold is `>`."""
    assert parse_sample_size("", row_count=150_000) is None


def test_enter_uses_the_large_default_above_the_threshold():
    assert parse_sample_size("", row_count=150_001) == DEFAULT_LARGE_SAMPLE


def test_explicit_none_means_full_dataset():
    assert parse_sample_size("none", row_count=1_000_000) is None
    assert parse_sample_size("  NONE  ", row_count=1_000_000) is None


def test_explicit_number_is_used():
    assert parse_sample_size("250", row_count=1_000) == 250
    assert parse_sample_size(" 250 ", row_count=1_000) == 250


@pytest.mark.parametrize("answer", ["0", "-5", "-1"])
def test_non_positive_sample_size_is_rejected(answer):
    with pytest.raises(PromptError, match="positive"):
        parse_sample_size(answer, row_count=100)


@pytest.mark.parametrize("answer", ["abc", "1.5", "ten"])
def test_non_numeric_sample_size_is_rejected(answer):
    with pytest.raises(PromptError, match="whole number"):
        parse_sample_size(answer, row_count=100)


def test_file_selection_defaults_to_last_file():
    assert parse_file_selection("", file_count=4) == [3]


def test_file_selection_parses_a_list():
    assert parse_file_selection("1,3", file_count=4) == [0, 2]
    assert parse_file_selection(" 2 , 1 ", file_count=4) == [1, 0]


def test_file_selection_deduplicates():
    assert parse_file_selection("2,2", file_count=4) == [1]


@pytest.mark.parametrize("answer", ["0", "5", "1,9", "-1"])
def test_file_selection_rejects_out_of_range(answer):
    with pytest.raises(PromptError, match="out of range"):
        parse_file_selection(answer, file_count=4)


@pytest.mark.parametrize("answer", ["abc", "1,abc", "1;;2"])
def test_file_selection_rejects_garbage_instead_of_guessing(answer):
    """Before: a typo discarded the valid part and silently used the last file."""
    with pytest.raises(PromptError):
        parse_file_selection(answer, file_count=4)


def test_file_selection_requires_files():
    with pytest.raises(PromptError):
        parse_file_selection("1", file_count=0)


def test_column_selection_splits_valid_and_unknown():
    valid, unknown = parse_column_selection(
        "City, Status,Nope", columns=["City", "Status", "amount"]
    )
    assert valid == ["City", "Status"]
    assert unknown == ["Nope"]


def test_column_selection_none_and_empty():
    assert parse_column_selection("none", ["a"]) == ([], [])
    assert parse_column_selection("", ["a"]) == ([], [])


def test_column_selection_deduplicates():
    valid, _ = parse_column_selection("City,City", columns=["City"])
    assert valid == ["City"]
