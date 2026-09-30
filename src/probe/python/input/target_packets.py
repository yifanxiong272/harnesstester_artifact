#!/usr/bin/env python3
"""Build packets from selected buggy-side units, test context, and constraints."""

from __future__ import annotations

import ast
from dataclasses import asdict
from pathlib import Path
from typing import Any

from common.utils.python.paths import safe_project_path
from probe.python.input.constraints import probe_constraints
from probe.python.input.module_contracts import (
    module_contracts,
    module_names,
    read_module,
)
from probe.python.input.public_routes import public_target_routes
from probe.python.input.target_units import load_target_units, source_file_index
from probe.python.models import TargetUnit
from probe.python.run.options import (
    TARGET_PROBING_TRACK,
    normalize_target_strategy,
)

LOW_SIGNAL_STEMS = {"__init__", "conftest"}


def build_target_packet(
    *,
    project: str,
    strategy: str,
    project_root: Path,
    target_units: list[dict[str, Any]],
    generated_test_roots: list[str] | None = None,
    python_import_roots: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Build JSON-ready records from the prepared buggy checkout."""

    strategy = normalize_target_strategy(strategy)
    units = load_target_units(project_root, target_units)
    if not units:
        raise SystemExit("case has no target units")
    generated_test_roots = generated_test_roots or ["tests/generated/benchmarkbr"]
    files = sorted({unit.filepath for unit in units})
    return {
        "project": project,
        "strategy": strategy,
        "track": TARGET_PROBING_TRACK,
        "target_units": [asdict(unit) for unit in units],
        "source_file_index": source_file_index(project_root, files),
        "existing_tests": existing_test_contexts(project_root, units),
        "constraints": probe_constraints(),
        "module_imports": module_import_contexts(project_root, files),
        "module_contracts": module_contracts(
            project_root,
            files,
            import_roots=python_import_roots,
        ),
        "public_target_routes": public_target_routes(
            project_root,
            units,
            import_roots=python_import_roots,
        ),
        "generated_test_roots": list(generated_test_roots),
    }


def existing_test_contexts(
    project_root: Path,
    units: list[TargetUnit],
    *,
    max_files: int = 2,
    max_chars: int = 7000,
) -> list[dict[str, Any]]:
    """Return bounded existing-test context selected by deterministic evidence."""

    matches = []
    for test_file in project_test_files(project_root):
        rel = test_file.relative_to(project_root).as_posix()
        match = test_match(test_file, rel, units=units)
        if match is None:
            continue
        matches.append((rel, match))

    result = []
    # Whole-file excerpts preserve the selected tests' import and fixture context.
    for rel, match in sorted(
        matches,
        key=lambda item: (int(item[1]["selection_order"]), len(item[0]), item[0]),
    )[:max_files]:
        text = safe_project_path(project_root, rel).read_text(
            encoding="utf-8",
            errors="replace",
        )
        truncated = len(text) > max_chars
        result.append(
            {
                "path": rel,
                "reason": str(match["reason"]),
                "content_excerpt": text[:max_chars],
                "selection_type": str(match["selection_type"]),
                "truncated": truncated,
                "target_unit_ids": [str(item) for item in match["target_unit_ids"]],
                "target_filepaths": [str(item) for item in match["target_filepaths"]],
            }
        )
    return result


def module_import_contexts(
    project_root: Path, files: list[str], *, max_lines: int = 80
) -> list[dict[str, Any]]:
    """Return top-level import blocks for target files."""

    excerpts: list[dict[str, Any]] = []
    for rel in sorted(set(files)):
        path = safe_project_path(project_root, rel)
        if not path.exists() or path.suffix != ".py":
            continue
        text, tree = read_module(path)
        if tree is None:
            continue
        spans = top_level_import_spans(tree)
        if not spans:
            continue
        start = min(span[0] for span in spans)
        end = min(max(span[1] for span in spans), start + max_lines - 1)
        excerpts.append(
            {
                "path": rel,
                "start_line": start,
                "end_line": end,
                "text": extract_lines(text, start, end),
            }
        )
    return excerpts


def top_level_import_spans(tree: ast.AST) -> list[tuple[int, int]]:
    spans = []
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            start = int(getattr(node, "lineno", 0) or 0)
            end = int(getattr(node, "end_lineno", start) or start)
            if start:
                spans.append((start, end))
    return spans


def extract_lines(text: str, start_line: int, end_line: int) -> str:
    lines = text.splitlines()
    return "\n".join(lines[max(0, start_line - 1) : max(0, end_line)])


def project_test_files(project_root: Path) -> list[Path]:
    files: list[Path] = []
    for root_name in ("tests", "test"):
        try:
            root = safe_project_path(project_root, root_name)
        except SystemExit:
            continue
        if root.exists():
            for path in root.rglob("*.py"):
                if not path.is_file():
                    continue
                rel = path.relative_to(project_root).as_posix()
                try:
                    safe_project_path(project_root, rel)
                except SystemExit:
                    continue
                files.append(path)
    return sorted(
        set(files), key=lambda path: path.relative_to(project_root).as_posix()
    )


def test_match(
    test_file: Path,
    relpath: str,
    *,
    units: list[TargetUnit],
) -> dict[str, Any] | None:
    """Match a test file by same module stem or static target-module import."""

    module, module_units = import_match(test_file, units=units)
    if module and module_units:
        return match_record(
            selection_order=0,
            selection_type="imports_target_module",
            reason=f"test file statically imports target module `{module}`",
            units=module_units,
        )
    stem_units = same_stem_units(relpath, units)
    if stem_units:
        stem = Path(stem_units[0].filepath).stem
        return match_record(
            selection_order=1,
            selection_type="same_stem_test_file",
            reason=f"same-stem test filename for target module stem `{stem}`",
            units=stem_units,
        )
    return None


def match_record(
    *, selection_order: int, selection_type: str, reason: str, units: list[TargetUnit]
) -> dict[str, Any]:
    return {
        "selection_order": selection_order,
        "selection_type": selection_type,
        "reason": reason,
        "target_unit_ids": sorted({unit.unit_id for unit in units}),
        "target_filepaths": sorted({unit.filepath for unit in units}),
    }


def same_stem_units(relpath: str, units: list[TargetUnit]) -> list[TargetUnit]:
    filename = Path(relpath).name
    if not filename.endswith(".py"):
        return []
    test_stem = filename[:-3].lower()
    for stem in target_stems(units):
        lowered = stem.lower()
        if test_stem in {
            f"test_{lowered}",
            f"{lowered}_test",
            f"{lowered}_tests",
        } or test_stem.startswith(f"test_{lowered}_"):
            return [unit for unit in units if Path(unit.filepath).stem == stem]
    return []


def target_stems(units: list[TargetUnit]) -> list[str]:
    stems = []
    for unit in units:
        stem = Path(unit.filepath).stem
        if stem and stem not in LOW_SIGNAL_STEMS and stem not in stems:
            stems.append(stem)
    return stems


def import_match(
    test_file: Path, *, units: list[TargetUnit]
) -> tuple[str, list[TargetUnit]]:
    """Return the target module imported by a test file, if any."""

    _, tree = read_module(test_file)
    if tree is None:
        return "", []
    modules = target_modules(units)
    parent_imports = {
        (module.rsplit(".", 1)[0], module.rsplit(".", 1)[1])
        for module in modules
        if "." in module
    }
    for node in ast.walk(tree):
        # Match imports against the target modules before the filename fallback.
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                matched = [
                    module
                    for module in modules
                    if name == module or name.startswith(f"{module}.")
                ]
                if matched:
                    module = sorted(matched, key=lambda item: (-len(item), item))[0]
                    return name, modules[module]
        elif isinstance(node, ast.ImportFrom):
            module = "." * int(node.level or 0) + (node.module or "")
            if module in modules:
                return module, modules[module]
            for parent, child in sorted(parent_imports):
                if module == parent and any(
                    alias.name == child for alias in node.names
                ):
                    full = f"{parent}.{child}"
                    return full, modules[full]
    return "", []


def target_modules(units: list[TargetUnit]) -> dict[str, list[TargetUnit]]:
    modules: dict[str, list[TargetUnit]] = {}
    for unit in units:
        # Matching considers checkout-relative names before src/lib aliases.
        for module in reversed(module_names(unit.filepath)):
            modules.setdefault(module, []).append(unit)
    return modules
