#!/usr/bin/env python3
from __future__ import annotations

from typing import Any


def score_test_coverage_delta(
    *,
    objective: dict[str, Any],
    accepted_coverage: dict[str, Any],
) -> dict[str, Any]:
    """Measure coverage added to the objective's current uncovered locations."""

    filepath = str(objective["filepath"])
    gap = objective.get("general_coverage", {})
    target_lines = {int(line) for line in gap.get("uncovered_lines", [])}
    target_branches = {str(arc) for arc in gap.get("uncovered_branches", [])}
    new_lines = covered_lines(accepted_coverage, filepath) & target_lines
    new_branches = covered_branch_keys(accepted_coverage, filepath) & target_branches
    return {
        "filepath": filepath,
        "target_lines": sorted(target_lines),
        "target_branches": sorted(target_branches),
        "new_lines": sorted(new_lines),
        "new_branches": sorted(new_branches),
        "coverage_delta": {
            "covered_lines": len(new_lines),
            "covered_branches": len(new_branches),
        },
    }


def score_general_coverage_delta(
    *, snapshot: dict[str, Any], accepted_coverage: dict[str, Any]
) -> dict[str, Any]:
    """Measure new ordinary project coverage against the current snapshot."""

    baseline = snapshot.get("general_coverage", {}).get("files", {})
    files = accepted_coverage.get("files", {})
    updates: list[dict[str, Any]] = []
    for filepath, item in files.items() if isinstance(files, dict) else ():
        if not isinstance(item, dict) or filepath not in baseline:
            continue
        current = baseline.get(filepath, {})
        lines = covered_lines(accepted_coverage, filepath) & {
            int(line) for line in current.get("uncovered_lines", [])
        }
        branches = covered_branch_keys(accepted_coverage, filepath) & {
            str(arc) for arc in current.get("uncovered_branches", [])
        }
        if lines or branches:
            updates.append(
                {
                    "filepath": filepath,
                    "new_lines": sorted(lines),
                    "new_branches": sorted(branches),
                }
            )
    return {
        "covered_lines": sum(len(item["new_lines"]) for item in updates),
        "covered_branches": sum(len(item["new_branches"]) for item in updates),
        "files": updates,
    }


def covered_lines(payload: dict[str, Any], filepath: str) -> set[int]:
    item = payload.get("files", {}).get(filepath)
    if not item:
        return set()
    return {int(line) for line in item.get("executed_lines", [])}


def covered_branch_keys(payload: dict[str, Any], filepath: str) -> set[str]:
    item = payload.get("files", {}).get(filepath)
    if not item:
        return set()
    result: set[str] = set()
    for raw in item.get("executed_branches", []):
        if not isinstance(raw, list) or len(raw) != 2:
            continue
        result.add(f"{int(raw[0])}->{int(raw[1])}")
    return result
