#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def build_ldh_coverage(
    regions: dict[str, Any], coverage: dict[str, Any]
) -> dict[str, Any]:
    """Project source/data LDH locations onto executable coverage facts.

    `regions` is the frozen source-flow artifact and `coverage` is the matching
    round-zero coverage.py projection. The returned file records are the only
    LDH state needed by the file-scoped workflow and by later coverage merges.
    """

    coverage_files = coverage.get("files")
    if not isinstance(coverage_files, dict):
        raise SystemExit("LDH coverage projection must contain object field files")

    files: dict[str, dict[str, Any]] = {}
    for filepath, region_lines in sorted(lines_by_file(regions).items()):
        measured = coverage_files.get(filepath)
        if not isinstance(measured, dict):
            raise SystemExit(f"LDH coverage is missing source file: {filepath}")
        executed = int_values(measured.get("executed_lines", []))
        missing = int_values(measured.get("missing_lines", []))
        lines = region_lines & (executed | missing)
        if not lines:
            continue
        files[filepath] = {
            "lines": sorted(lines),
            "covered_lines": sorted(lines & executed),
            "uncovered_lines": sorted(lines - executed),
            "covered_branches": branch_keys(
                measured.get("executed_branches", []), lines
            ),
            "uncovered_branches": branch_keys(
                measured.get("missing_branches", []), lines
            ),
        }
    return {"files": files}


def lines_by_file(regions: dict[str, Any]) -> dict[str, set[int]]:
    """Return the union of source and data-dependence lines in each file."""

    result: dict[str, set[int]] = {}
    for key in ("sources", "data_dependence"):
        items = regions.get(key, [])
        for item in items if isinstance(items, list) else ():
            location = item.get("location", {}) if isinstance(item, dict) else {}
            filepath = location.get("filepath")
            start = location.get("start_line")
            end = location.get("end_line", start)
            if not isinstance(filepath, str) or start is None:
                continue
            result.setdefault(filepath, set()).update(range(int(start), int(end) + 1))
    return result


def branch_keys(values: Any, source_lines: set[int]) -> list[str]:
    """Normalize coverage.py arcs whose branch source is an LDH line."""

    result: set[str] = set()
    for value in values if isinstance(values, list) else ():
        if not isinstance(value, list) or len(value) != 2:
            continue
        source, destination = int(value[0]), int(value[1])
        if source in source_lines:
            result.add(f"{source}->{destination}")
    return sorted(result)


def int_values(values: Any) -> set[int]:
    return {
        int(value)
        for value in (values if isinstance(values, list) else ())
        if not isinstance(value, bool)
    }
