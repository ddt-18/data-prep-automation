# 📊 Data Cleaning & Profiling Automation

A small, tested Python project that automates the boring first hour of data analysis:
load a file, clean it, see exactly what changed, and get charts plus a profiling report.

Built to be read as well as run: the cleaning logic lives in importable modules with
tests, not in one long notebook cell.

**Current status:** the cleaning, loading, exporting and chart code is covered by an
automated test suite (203 tests) that passes on pandas 2.2.3 and 3.1.0. The HTML
report is a thin wrapper around `ydata-profiling` and is tested separately. See
[Tested behaviour](#-tested-behaviour) and [Known limitations](#-known-limitations).

---

## 🎯 What it does

- **Loads** CSV, Excel, JSON / JSON Lines and Parquet files. CSV encodings are
  detected properly (UTF-8, UTF-8 with BOM, UTF-16, Windows-1252) instead of being
  guessed, and a file that cannot be decoded raises a clear error rather than
  "loading successfully" as a table of `NaN`.
- **Cleans** with explicit options: drop or fill missing values, remove duplicates
  (whole rows *or* a key such as `Booking ID`), and make column names safe and unique.
- **Never converts text to numbers by default.** ZIP codes, IDs and phone numbers keep
  their leading zeros. Conversion is opt-in and still skips identifier-like columns.
- **Reports what changed** in a `CleaningSummary` you can print, log or serialise to JSON.
- **Exports** the cleaned data to CSV (and Excel when it fits), draws bar/pie charts and
  builds an interactive HTML report with `ydata-profiling`.

---

## ⚙️ Requirements and setup (verified)

- Python **3.10+** (the code uses `X | None` type hints)
- Run these from the project root:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` pins the versions used for testing and installs this project in
editable mode, so `import data_prep` works. Then open the notebook:

```bash
jupyter notebook data_preprocessing_automation.ipynb
```

If you only want to use the code, `pip install -e .` is enough (dependencies come from
`pyproject.toml`).

---

## 📂 Project structure

```
project/
├── src/data_prep/                 # the library (importable, no side effects)
│   ├── loading.py                 #   read files + encoding detection
│   ├── cleaning.py                #   CleaningOptions, clean_data, CleaningSummary
│   ├── names.py                   #   safe, unique column names and filenames
│   ├── exporting.py               #   CSV / Excel output
│   ├── visualization.py           #   bar and pie charts
│   ├── reporting.py               #   HTML report (optional dependency)
│   └── interactive.py             #   parsing for the notebook's questions
├── tests/                         # pytest suite (203 tests)
├── data_preprocessing_automation.ipynb   # interactive front end
├── requirements.txt               # pinned dependencies
├── pyproject.toml                 # package metadata + pytest config
└── output/                        # generated: data, charts, reports, logs
```

Put your own files in a folder of your choice (for example `Datasets/`); they are
git-ignored, so real data never gets committed by accident.

---

## 🚀 How to use

### The notebook

1. Run the setup cell (imports only - it does not read data or prompt).
2. Point it at your folder and pick one or more files by number.
3. Answer the cleaning questions. An empty answer means "use the default shown";
   a typo re-asks instead of silently choosing something else.
4. Read the `📋 What changed` block, then find your files in `output/`.

Output names are unchanged from earlier versions:

```
output/<file>_cleaned_<YYYYmmdd_HHMMSS>.csv
output/<file>_cleaned_<YYYYmmdd_HHMMSS>.xlsx     (only when it fits Excel)
output/<file>_plots/bar_<column>.png, pie_<column>.png
output/<file>_report_<YYYYmmdd>.html
output/processing_<YYYYmmdd_HHMMSS>.log
```

### From Python

```python
from data_prep import CleaningOptions, clean_data, list_data_files, load_table, save_outputs

df = load_table("Datasets/bookings.csv")

cleaned, summary = clean_data(
    df,
    CleaningOptions(
        missing_values="fill",
        fill_numeric="median",              # safer than the mean for skewed money columns
        drop_duplicates=True,
        duplicate_subset=["Booking ID"],    # compare only the identifying column
    ),
)

for line in summary.to_lines():
    print(line)

save_outputs(cleaned, "bookings", "output")
# summary.to_dict() is JSON-serialisable if you want a machine-readable report
```

---

## 🧠 Design decisions that affect data correctness

These are deliberate, and each one is covered by a test.

**1. Text is never converted to numbers automatically.**
The previous version ran `pd.to_numeric` over every column, which turned `"01234"` into
`1234` and `"007"` into `7`. Now the default is `numeric_coercion="none"`. If you opt in
with `"safe"`, a column is still left alone when its name looks identifier-like
(`id`, `zip`, `phone`, `code`, …), when values have leading zeros, when they are long
digit strings, or when any value is not numeric. Every decision is recorded in
`summary.coercions`.

**2. Missing values are filled in a way that cannot silently do nothing.**
Filling assigns the result back to the DataFrame and is verified by tests. You can choose
`mean` or `median` for numbers, and `mode` or a constant for text. Columns that are at
least 50% empty are flagged in the summary, because filling them means most of their
values were never recorded.

**3. "Drop duplicate rows" has two meanings - be explicit.**
Comparing every column removes only byte-identical rows. In the sample dataset that
finds **0** duplicates, while there are **1,233** repeated `Booking ID`s. Pass
`duplicate_subset=["Booking ID"]` (or answer the notebook's key-column question) when
you mean "one row per key". The summary always states which comparison was used.

**4. Column names are sanitised and made unique.**
`Total Price` and `Total_Price` used to collapse into one column, which then crashed
groupby, the charts and the profiler. Duplicates now get `_2`, `_3`, … suffixes and a
warning. Non-string headers (for example an Excel year `2024`) no longer raise.

**5. An empty result is not written by default.**
If cleaning removes every row, `save_outputs` raises `EmptyOutputError` instead of writing
a 0-row CSV, printing success and letting you believe the job worked. Pass
`allow_empty=True` if that is really what you want.

**6. Encoding detection never guesses silently.**
Byte-order marks are honoured, and a candidate encoding is only accepted if the decoded
text actually looks like text. This is why a UTF-16 file is now read correctly instead of
producing a table of `NaN`. You can override with `load_table(path, encoding="cp1252")`.

**7. Charts say when they are based on a sample.**
With `sample_size=50000` on a 150,000-row file, titles read
`Top 10 Vehicle Type (n=50,000 sample)`.

**8. Excel's row limit includes the header.**
Export is skipped when `rows + 1 > 1,048,576`, so a file that is exactly at the limit no
longer fails halfway through.

---

## ✅ Tested behaviour

```bash
python -m pytest -q
```

Results from the environment this change was built in:

| Environment | Result |
|---|---|
| pandas 2.2.3, matplotlib 3.10.0, ydata-profiling 4.18.4 | **203 passed** |
| pandas 3.1.0, matplotlib 3.11.2, no ydata-profiling | **200 passed, 1 skipped** (report tests skip cleanly) |

The suite covers, with one test per bug where relevant:

- encoding detection: UTF-8, BOM, UTF-16, Windows-1252, 0-byte files, binary junk
- loading: CSV/Excel/JSON/JSON Lines/Parquet, multi-sheet selection, missing files
- missing values: mean/median/mode/constant fills, nullable booleans, integer columns
  that cannot hold a fraction, destructive `dropna` warnings
- duplicates: whole-row versus keyed comparison, `keep="last"`, unknown keys
- identifiers: `01234`, `007`, quoted IDs, `paid`/`valid`/`width` not mistaken for IDs
- column names: collisions, whitespace, non-string labels, unsafe characters
- outputs: empty-data refusal, Excel boundary, leading zeros surviving the CSV round trip
- charts: unsafe column names, auto-selection, pie slice limits
- prompts: an empty answer never re-prompts forever
- the notebook itself, executed end-to-end with simulated keystrokes
- the real 150k-row dataset, recovered from git history (skipped in shallow clones)

Two source-level guards also fail the build if `errors="ignore"` or
`fillna(..., inplace=True)` is reintroduced, since both break under pandas 3.

> Note: the chained-`inplace` bug is invisible on pandas 2.x (where it still mutates in
> place) and only fails on pandas 3.x. Running the suite on both versions is what keeps
> that fix honest.

---

## 🔒 Privacy: the outputs contain your data

- The HTML report embeds **sample rows and value frequencies** from your file. Treat it
  exactly like the original dataset.
- Cleaned CSVs, Excel files, charts and reports all land in `output/`, which is
  git-ignored, together with `Datasets/` and common data extensions.
- Nothing is uploaded anywhere: there are no network calls in this project.

---

## 📌 The sample dataset

The README examples use `ncr_ride_bookings.csv` (150,000 rows × 21 columns, a public
teaching dataset of NCR ride bookings). **It is not in the working tree** - it was removed
in commit `1462b01`. It still exists in git history, so you can recover it with:

```bash
git show 6aa6226:Datasets/ncr_ride_bookings.csv > Datasets/ncr_ride_bookings.csv
```

If you clone shallowly (`--depth 1`) that commit is not available; download the dataset
from its original source instead, and please record the source and licence here.

Known quirks of this file, which the tests assert: every `Booking ID`/`Customer ID` is
wrapped in literal quote characters (`"CNR5884300"`), there are 1,233 repeated booking
IDs, and every row has at least one empty column.

---

## ⚠️ Known limitations

- Only the **first Excel sheet** is read by default (`load_table(..., sheet_name=...)`
  selects another); the notebook does not ask which sheet.
- **Dates are not parsed.** `Date`/`Time` stay as text, so time-series work needs a manual
  `pd.to_datetime` step.
- The report filename has no time component, so a second run on the same day overwrites
  the first report for that dataset.
- Large files are read whole into memory; there is no chunked or out-of-core mode yet.
- No CLI: the interactive notebook is the only entry point.
- `ydata-profiling` warns on import that it is being renamed to `fg-data-profiling`; the
  pinned version still works.
- The library prints nothing and logs to the `data_prep` logger; configure logging in your
  own script if you want to see it.

---

## 🙋 Honesty note

This project was built with AI assistance (ChatGPT + Grok) and later reviewed and
restructured with an AI coding agent. The goal is a small tool that is honest about what
it does: tested cleaning steps, visible summaries, and limitations written down instead of
hidden.

## 📜 License

[MIT](LICENSE) - use it, tweak it, share it.
