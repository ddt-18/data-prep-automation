"""data_prep - a small, testable core for automated data preparation.

The package is split by responsibility so each part can be tested and reused:

``loading``       read CSV / Excel / JSON / Parquet safely
``cleaning``      clean a DataFrame and describe what changed
``exporting``     write CSV / Excel outputs
``visualization`` bar and pie charts
``reporting``     HTML profiling report (optional dependency)
``interactive``   parse answers typed at a prompt (no I/O)

Typical use::

    from data_prep import CleaningOptions, clean_data, load_table, save_outputs

    df = load_table("datasets/bookings.csv")
    cleaned, summary = clean_data(
        df,
        CleaningOptions(missing_values="fill", fill_numeric="median"),
    )
    print("\\n".join(summary.to_lines()))
    save_outputs(cleaned, "bookings", "output")

Nothing runs on import: there are no prompts, no directories created and no
logging configured. The notebook is the interactive layer on top.
"""

from __future__ import annotations

from .cleaning import (
    CleaningOptions,
    CleaningSummary,
    clean_data,
    identifier_reason,
)
from .errors import (
    DataPrepError,
    EmptyFileError,
    EmptyOutputError,
    EncodingDetectionError,
    LoadError,
    UnsupportedFormatError,
)
from .exporting import OutputPaths, save_outputs
from .interactive import (
    PromptError,
    parse_column_selection,
    parse_file_selection,
    parse_sample_size,
)
from .loading import detect_csv_encoding, list_data_files, load_table
from .reporting import build_report
from .visualization import (
    auto_select_columns,
    make_charts,
    select_plot_frame,
)

__version__ = "0.1.0"

__all__ = [
    "CleaningOptions",
    "CleaningSummary",
    "DataPrepError",
    "EmptyFileError",
    "EmptyOutputError",
    "EncodingDetectionError",
    "LoadError",
    "OutputPaths",
    "PromptError",
    "UnsupportedFormatError",
    "__version__",
    "auto_select_columns",
    "build_report",
    "clean_data",
    "detect_csv_encoding",
    "identifier_reason",
    "list_data_files",
    "load_table",
    "make_charts",
    "parse_column_selection",
    "parse_file_selection",
    "parse_sample_size",
    "save_outputs",
    "select_plot_frame",
]
