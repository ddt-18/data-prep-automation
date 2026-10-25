"""Exceptions raised by :mod:`data_prep`.

Every error message is written for a beginner: it says what went wrong *and*
what to do next. All messages are plain ASCII so they print safely on Windows
consoles that cannot encode emoji.
"""

from __future__ import annotations


class DataPrepError(Exception):
    """Base class for all errors raised by this package."""


class LoadError(DataPrepError):
    """A dataset could not be read."""


class EmptyFileError(LoadError):
    """The file has no content at all (0 bytes)."""


class EncodingDetectionError(LoadError):
    """The text encoding of a CSV could not be determined."""


class UnsupportedFormatError(LoadError):
    """The file extension is not one we support."""


class EmptyOutputError(DataPrepError):
    """Refusing to write an empty dataset.

    Writing a 0-row file looks like success but silently destroys the data,
    so callers must opt in with ``allow_empty=True``.
    """
