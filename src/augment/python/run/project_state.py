#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from augment.python.models import TestProposal
from augment.python.project_files import (
    ignore_copy,
    normalized_append_code,
)


def current_project_root(run_dir: Path, frozen_root: Path) -> Path:
    return run_dir / "workspaces" / "current" / frozen_root.name


def staging_project_root(run_dir: Path, frozen_root: Path, sample_id: str) -> Path:
    return run_dir / "workspaces" / "staging" / sample_id / frozen_root.name


def accepted_snapshot_path(run_dir: Path, sample_id: str, test_file: str) -> Path:
    """Return the canonical run-local snapshot for one accepted test file."""

    if not sample_id:
        raise SystemExit("accepted test snapshot requires a sample_id")
    return _local_path(
        run_dir / "accepted" / "files",
        Path(sample_id) / Path(test_file),
    )


def initialize_current_project(frozen_root: Path, current_root: Path) -> None:
    """Create the rolling project copy for one invocation."""
    current_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(frozen_root, current_root, ignore=ignore_copy)


def create_staging_project(current_root: Path, staging_root: Path) -> None:
    """Create a disposable validation copy from the current rolling project."""

    if staging_root.parent.exists():
        shutil.rmtree(staging_root.parent)
    staging_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(current_root, staging_root, ignore=ignore_copy)


def materialize_in_project(
    project_root: Path, proposal: TestProposal
) -> dict[str, Any]:
    """Write a proposal to a new test file in a project copy."""

    target = _local_path(project_root, Path(proposal.test_file))
    if target.exists():
        raise SystemExit(f"generated test file already exists: {proposal.test_file}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        normalized_append_code(proposal.append_code),
        encoding="utf-8",
    )
    return {
        "copy_root": str(project_root),
        "test_file": proposal.test_file,
        "created_new_test_file": True,
        "expected_nodeids": proposal.expected_nodeids,
    }


def persist_generated_snapshot(
    *,
    run_dir: Path,
    sample_id: str,
    current_root: Path,
    test_file: str,
    generated_snapshot: Path,
) -> dict[str, str]:
    """Persist the chosen generated file after candidate comparison."""

    if not generated_snapshot.is_file():
        raise SystemExit(
            f"accepted generated test snapshot is missing: {generated_snapshot}"
        )
    content = generated_snapshot.read_text(encoding="utf-8", errors="replace")
    relative = Path(test_file)
    snapshot = accepted_snapshot_path(run_dir, sample_id, test_file)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(content, encoding="utf-8")
    destination = _local_path(current_root, relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return {
        "accepted_file_snapshot": str(snapshot),
        "accepted_project_path": test_file,
    }


def cleanup_staging(staging_root: Path) -> None:
    root = staging_root.parent
    if root.exists():
        shutil.rmtree(root)


def cleanup_workspaces(run_dir: Path) -> None:
    """Remove reproducible rolling and staging copies after an invocation."""

    workspaces = run_dir / "workspaces"
    if workspaces.exists():
        shutil.rmtree(workspaces)


def _local_path(root: Path, relative: Path) -> Path:
    """Resolve a local path and reject symlink escapes beyond `root`."""

    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise SystemExit(f"unsafe project-relative path: {relative}")
    resolved_root = root.resolve()
    resolved = (resolved_root / relative).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise SystemExit(f"project-relative path escapes its root: {relative}") from exc
    return resolved
