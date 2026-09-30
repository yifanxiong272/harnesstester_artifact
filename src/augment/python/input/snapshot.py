#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

from augment.python.input.ldh_coverage import build_ldh_coverage
from common.utils.python.json_io import read_json


def build_initial_metric_snapshot(
    base_input_path: Path,
    *,
    project_root: Path | None = None,
    python: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Project supplied LDH regions onto baseline executable coverage."""

    base_input = load_base_input(base_input_path)
    project = str(base_input["project"])
    input_root = base_input_path.resolve().parent
    project_root = (
        project_root.resolve()
        if project_root is not None
        else resolve_base_path(base_input["project_root"], input_root)
    )
    ldh = object_field(base_input, "ldh")
    general_cov = object_field(base_input, "general_cov")
    runtime = object_field(base_input, "runtime")

    regions_path = resolve_base_path(ldh["regions_json"], input_root)
    general_coverage_path = resolve_base_path(general_cov["coverage_json"], input_root)

    regions = read_json(regions_path)
    coverage = load_coverage_facts(general_coverage_path)
    snapshot = {
        "project": project,
        "ldh_coverage": build_ldh_coverage(regions, coverage),
        "general_coverage": normalize_general_coverage(coverage),
    }
    validate_metric_snapshot(snapshot)
    return (
        snapshot,
        {
            "project": project,
            "project_root": str(project_root),
            "python": str(
                python.absolute()
                if python
                else (input_root / runtime["python"]).absolute()
            ),
            "coverage_source": str(runtime["coverage_source"]),
            "test_pythonpath": string_list(runtime.get("test_pythonpath")),
        },
    )


def load_base_input(path: Path) -> dict[str, Any]:
    data = read_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"expected base input object: {path}")
    for key in (
        "project",
        "project_root",
        "ldh",
        "general_cov",
        "runtime",
    ):
        if key not in data:
            raise SystemExit(f"base input missing {key}: {path}")
    ldh = object_field(data, "ldh")
    general_cov = object_field(data, "general_cov")
    runtime = object_field(data, "runtime")
    required_fields = (
        ("ldh", ldh, ("regions_json",)),
        ("general_cov", general_cov, ("coverage_json",)),
        ("runtime", runtime, ("python", "coverage_source")),
    )
    for section, values, keys in required_fields:
        for key in keys:
            if not values.get(key):
                raise SystemExit(f"base input {section} missing {key}: {path}")
    return data


def load_coverage_facts(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), dict):
        raise SystemExit(f"coverage input must contain object field files: {path}")
    return payload


def normalize_general_coverage(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize one coverage.py JSON report for file-level guidance."""

    files = payload["files"]
    normalized: dict[str, dict[str, Any]] = {}
    for filepath, item in files.items():
        if not isinstance(item, dict):
            continue
        covered_lines = positive_ints(item.get("executed_lines", []))
        missing_lines = positive_ints(item.get("missing_lines", []))
        covered_branches = branch_strings(item.get("executed_branches", []))
        missing_branches = branch_strings(item.get("missing_branches", []))
        normalized[str(filepath)] = {
            "covered_lines": sorted(covered_lines),
            "uncovered_lines": sorted(missing_lines),
            "total_lines": len(covered_lines | missing_lines),
            "covered_branches": sorted(covered_branches),
            "uncovered_branches": sorted(missing_branches),
            "total_branches": len(covered_branches | missing_branches),
        }
    return {"files": normalized, "totals": coverage_totals(normalized.values())}


def coverage_totals(files: Any) -> dict[str, int]:
    rows = list(files)
    total_lines = sum(int(item.get("total_lines") or 0) for item in rows)
    covered_lines = sum(len(item.get("covered_lines", [])) for item in rows)
    total_branches = sum(int(item.get("total_branches") or 0) for item in rows)
    covered_branches = sum(len(item.get("covered_branches", [])) for item in rows)
    return {
        "covered_lines": covered_lines,
        "total_lines": total_lines,
        "covered_branches": covered_branches,
        "total_branches": total_branches,
    }


def positive_ints(values: Any) -> set[int]:
    result: set[int] = set()
    for value in values if isinstance(values, list) else ():
        try:
            line = int(value)
        except (TypeError, ValueError):
            continue
        if line > 0:
            result.add(line)
    return result


def branch_strings(values: Any) -> set[str]:
    return {
        f"{int(value[0])}->{int(value[1])}"
        for value in (values if isinstance(values, list) else ())
        if isinstance(value, list) and len(value) == 2
    }


def object_field(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise SystemExit(f"base input field must be an object: {key}")
    return value


def resolve_base_path(value: object, root: Path) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else (root / path).resolve()


def string_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SystemExit("runtime.test_pythonpath must be a JSON list when provided")
    return [str(item) for item in value if str(item)]


def validate_metric_snapshot(snapshot: dict[str, Any]) -> None:
    if not snapshot.get("project"):
        raise SystemExit("metric snapshot missing project")
    ldh = snapshot.setdefault("ldh_coverage", {"files": {}})
    snapshot.setdefault("general_coverage", {"files": {}, "totals": {}})
    if not isinstance(ldh.get("files"), dict):
        raise SystemExit("metric snapshot ldh_coverage.files must be an object")
