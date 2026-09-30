#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Artifact source directory used by test subprocesses.
STUDY_SRC_ROOT = Path(__file__).resolve().parents[3]
STUDY_ROOT = STUDY_SRC_ROOT.parent


def rel_path(path: Path, root: Path) -> str:
    """Return the resolved path relative to the resolved root, using POSIX separators."""

    return path.resolve().relative_to(root.resolve()).as_posix()


def safe_relative_path(path: str) -> None:
    """Reject absolute paths and parent-directory components."""
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise SystemExit(f"unsafe relative path: {path}")


def safe_project_path(root: Path, path: str) -> Path:
    """Join a relative path to `root`, checking that symlinks remain inside it."""

    safe_relative_path(path)
    resolved_root = root.resolve()
    candidate = resolved_root / path
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(resolved_root):
        raise SystemExit(f"project path escapes checkout through a symlink: {path}")
    return candidate
