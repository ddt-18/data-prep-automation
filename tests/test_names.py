"""Column-name and filename normalisation."""

from __future__ import annotations

import pytest

from data_prep.names import (
    FALLBACK_COLUMN_NAME,
    FALLBACK_FILENAME,
    FilenameRegistry,
    build_unique_names,
    sanitize_column_name,
    slugify_filename,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("City", "City"),
        ("Total Price", "Total_Price"),
        ("Total  Price ", "Total_Price"),   # repeated/edge whitespace collapses
        ("A  B", "A_B"),                   # was "A__B" before
        ("a/b", "a_b"),
        ("50%", "50"),
        ("  ", FALLBACK_COLUMN_NAME),
        ("", FALLBACK_COLUMN_NAME),
        ("Booking ID", "Booking_ID"),
    ],
)
def test_sanitize_column_name(raw, expected):
    assert sanitize_column_name(raw) == expected


def test_sanitize_handles_non_string_labels():
    """Excel headers like a year arrive as integers.

    Before: ``AttributeError: 'int' object has no attribute 'strip'``.
    """
    assert sanitize_column_name(2024) == "2024"
    assert sanitize_column_name(3.5) == "3_5"


def test_sanitize_keeps_unicode_letters_recognisable():
    # Non-ASCII characters are replaced rather than dropped silently becoming "".
    assert sanitize_column_name("Ville") == "Ville"
    assert sanitize_column_name("naïve") == "na_ve"


def test_build_unique_names_resolves_collisions():
    cleaned, renamed, collisions = build_unique_names(["Total Price", "Total_Price"])

    assert cleaned == ["Total_Price", "Total_Price_2"]
    assert collisions == ["Total_Price"]
    assert renamed == [("Total Price", "Total_Price"), ("Total_Price", "Total_Price_2")]


def test_build_unique_names_preserves_order_and_skips_clean_names():
    cleaned, renamed, collisions = build_unique_names(["b", "a", "c"])

    assert cleaned == ["b", "a", "c"]
    assert renamed == []
    assert collisions == []


def test_build_unique_names_respects_taken_names():
    cleaned, _, collisions = build_unique_names(["a"], taken=["a"])
    assert cleaned == ["a_2"]
    assert collisions == ["a"]


def test_build_unique_names_handles_three_way_collision():
    cleaned, _, _ = build_unique_names(["a b", "a_b", "a  b"])
    assert cleaned == ["a_b", "a_b_2", "a_b_3"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Pickup Location", "Pickup_Location"),
        ("a/b", "a_b"),
        ("../../escaped", "escaped"),
        ("..", FALLBACK_FILENAME),
        ("", FALLBACK_FILENAME),
        ("a:b*c?", "a_b_c"),
    ],
)
def test_slugify_filename_cannot_change_the_path(raw, expected):
    """A column name must never be able to escape the output folder."""
    slug = slugify_filename(raw)
    assert slug == expected
    assert "/" not in slug and "\\" not in slug and not slug.startswith(".")


def test_slugify_filename_truncates_long_names():
    slug = slugify_filename("x" * 500)
    assert len(slug) == 80


def test_filename_registry_keeps_names_unique():
    registry = FilenameRegistry()
    assert registry.slug("a/b") == "a_b"
    assert registry.slug("a:b") == "a_b_2"
    assert registry.slug("a b") == "a_b_3"
