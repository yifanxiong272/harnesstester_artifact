#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from augment.python.input.snapshot import branch_strings as branch_keys


def update_snapshot(
    snapshot: dict[str, Any],
    coverage: dict[str, Any],
) -> None:
    """Merge accepted-test coverage into the in-memory metric snapshot."""

    files = coverage.get("files", {}) if isinstance(coverage.get("files"), dict) else {}
    ldh_files = snapshot.get("ldh_coverage", {}).get("files", {})
    if not isinstance(ldh_files, dict):
        raise SystemExit("metric snapshot ldh_coverage.files must be an object")

    for filepath, target in ldh_files.items():
        file_cov = files.get(filepath)
        if not isinstance(file_cov, dict):
            continue
        executed_lines = int_values(file_cov.get("executed_lines", []))
        ldh_lines = int_values(target.get("lines", []))
        covered_before = int_values(target.get("covered_lines", []))
        newly_covered = sorted((executed_lines & ldh_lines) - covered_before)

        executed_branches = branch_keys(file_cov.get("executed_branches", []))
        uncovered_branches = {str(value) for value in target["uncovered_branches"]}
        newly_covered_branches = sorted(uncovered_branches & executed_branches)
        if not newly_covered and not newly_covered_branches:
            continue

        covered_after = covered_before | set(newly_covered)
        target["covered_lines"] = sorted(covered_after)
        target["uncovered_lines"] = sorted(ldh_lines - covered_after)

        if newly_covered_branches:
            target["uncovered_branches"] = sorted(
                uncovered_branches - set(newly_covered_branches)
            )
            target["covered_branches"] = sorted(
                {str(value) for value in target["covered_branches"]}
                | set(newly_covered_branches)
            )

    update_general_coverage(snapshot, coverage)


def update_general_coverage(snapshot: dict[str, Any], coverage: dict[str, Any]) -> None:
    """Merge accepted-test coverage into the ordinary whole-project facts."""

    general = snapshot.setdefault("general_coverage", {"files": {}, "totals": {}})
    current_files = general.setdefault("files", {})
    measured_files = coverage.get("files", {})
    if not isinstance(current_files, dict) or not isinstance(measured_files, dict):
        return

    for filepath, measured in measured_files.items():
        current = current_files.get(filepath)
        if not isinstance(current, dict) or not isinstance(measured, dict):
            continue
        covered_before = int_values(current.get("covered_lines", []))
        uncovered_before = int_values(current.get("uncovered_lines", []))
        new_lines = sorted(
            int_values(measured.get("executed_lines", [])) & uncovered_before
        )
        covered_branches_before = {
            str(value) for value in current.get("covered_branches", [])
        }
        uncovered_branches_before = {
            str(value) for value in current.get("uncovered_branches", [])
        }
        new_branches = sorted(
            branch_keys(measured.get("executed_branches", []))
            & uncovered_branches_before
        )
        if not new_lines and not new_branches:
            continue
        current["covered_lines"] = sorted(covered_before | set(new_lines))
        current["uncovered_lines"] = sorted(uncovered_before - set(new_lines))
        current["covered_branches"] = sorted(
            covered_branches_before | set(new_branches)
        )
        current["uncovered_branches"] = sorted(
            uncovered_branches_before - set(new_branches)
        )
    general["totals"] = general_totals(current_files)


def general_totals(files: dict[str, Any]) -> dict[str, int]:
    rows = [item for item in files.values() if isinstance(item, dict)]
    return {
        "covered_lines": sum(len(item.get("covered_lines", [])) for item in rows),
        "total_lines": sum(int(item.get("total_lines") or 0) for item in rows),
        "covered_branches": sum(len(item.get("covered_branches", [])) for item in rows),
        "total_branches": sum(int(item.get("total_branches") or 0) for item in rows),
    }


def coverage_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return a compact read-only summary for one metric snapshot."""

    files = snapshot.get("ldh_coverage", {}).get("files", {})
    if not isinstance(files, dict):
        raise SystemExit("metric snapshot ldh_coverage.files must be an object")
    total_ldh = 0
    covered_ldh = 0
    uncovered_ldh = 0
    total_branches = 0
    covered_branches = 0
    for target in files.values():
        if not isinstance(target, dict):
            continue
        ldh_lines = int_values(target.get("lines", []))
        covered_lines = int_values(target.get("covered_lines", []))
        uncovered_lines = int_values(target.get("uncovered_lines", []))
        total_ldh += len(ldh_lines)
        covered_ldh += len(covered_lines)
        uncovered_ldh += len(uncovered_lines)
        total_branches += len(target.get("covered_branches", [])) + len(
            target.get("uncovered_branches", [])
        )
        covered_branches += len(target.get("covered_branches", []))

    general = snapshot.get("general_coverage", {}).get("totals", {})
    return {
        "ldh_lines": {
            "total": total_ldh,
            "covered": covered_ldh,
            "uncovered": uncovered_ldh,
            "coverage": ratio(covered_ldh, total_ldh),
        },
        "branches": {
            "total": total_branches,
            "covered": covered_branches,
            "uncovered": max(0, total_branches - covered_branches),
            "coverage": ratio(covered_branches, total_branches),
        },
        "project_coverage": {
            "lines": {
                "total": int(general.get("total_lines") or 0),
                "covered": int(general.get("covered_lines") or 0),
                "coverage": ratio(
                    int(general.get("covered_lines") or 0),
                    int(general.get("total_lines") or 0),
                ),
            },
            "branches": {
                "total": int(general.get("total_branches") or 0),
                "covered": int(general.get("covered_branches") or 0),
                "coverage": ratio(
                    int(general.get("covered_branches") or 0),
                    int(general.get("total_branches") or 0),
                ),
            },
        },
    }


def int_values(values: Any) -> set[int]:
    result: set[int] = set()
    if not isinstance(values, list):
        return result
    for value in values:
        try:
            result.add(int(value))
        except (TypeError, ValueError):
            continue
    return result


def ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None
