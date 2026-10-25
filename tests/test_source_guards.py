"""Guards against reintroducing the pandas 3 breakages.

Reading the source with ``ast`` is more precise than grepping: the docstrings
intentionally mention the old calls, so a text search would give false alarms.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
PACKAGE_FILES = sorted(SRC.glob("data_prep/*.py"))


def _calls(module: ast.AST):
    for node in ast.walk(module):
        if isinstance(node, ast.Call):
            yield node


@pytest.mark.parametrize("path", PACKAGE_FILES, ids=lambda p: p.name)
def test_no_deprecated_inplace_assignment(path):
    """``df[col].fillna(..., inplace=True)`` is a silent no-op on pandas 3."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = []
    for node in _calls(tree):
        name = getattr(node.func, "attr", None)
        if name in {"fillna", "dropna", "drop_duplicates", "replace", "sort_values"}:
            if any(
                keyword.arg == "inplace" and getattr(keyword.value, "value", None)
                for keyword in node.keywords
            ):
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, f"inplace=True is unsupported on pandas 3: {offenders}"


@pytest.mark.parametrize("path", PACKAGE_FILES, ids=lambda p: p.name)
def test_no_to_numeric_errors_ignore(path):
    """``errors='ignore'`` was removed in pandas 3 and raised ValueError."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = []
    for node in _calls(tree):
        if getattr(node.func, "attr", None) == "to_numeric":
            for keyword in node.keywords:
                if keyword.arg == "errors" and getattr(keyword.value, "value", None) == "ignore":
                    offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, f"errors='ignore' was removed in pandas 3: {offenders}"


def test_importing_the_package_has_no_side_effects(tmp_path):
    """No prompts, no output folder, no logging configured just by importing."""
    env = {"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [sys.executable, "-c", "import data_prep; print(data_prep.__version__)"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "0.1.0"
    assert list(tmp_path.iterdir()) == []
