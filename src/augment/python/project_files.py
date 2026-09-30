#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

IGNORED_NAMES = {
    ".cache",
    ".git",
    ".home",
    ".test_augment_home",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
}


def ignore_copy(_dirpath: str, names: list[str]) -> set[str]:
    """Exclude reproducible runtime and dependency artifacts from project copies."""

    return {name for name in names if ignored_name(name)}


def normalized_append_code(code: str) -> str:
    return code.rstrip() + "\n"


def run_directory(out_root: Path, run_id: str) -> Path:
    """Resolve one run directory without allowing path traversal."""

    if not run_id or Path(run_id).name != run_id or run_id in {".", ".."}:
        raise SystemExit(f"run_id must be a single path component: {run_id!r}")
    return (out_root / "runs" / run_id).resolve()


def ignored_name(name: str) -> bool:
    return (
        name in IGNORED_NAMES
        or name.endswith(".pyc")
        or name == ".coverage"
        or name.startswith(".coverage.")
    )
