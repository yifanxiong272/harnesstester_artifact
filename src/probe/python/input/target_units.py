"""Load selected target units from the prepared buggy checkout."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from common.utils.python.paths import safe_project_path
from probe.python.models import TargetUnit


def source_file_index(project_root: Path, files: list[str]) -> list[dict[str, Any]]:
    result = []
    for path in sorted(set(files)):
        file_path = safe_project_path(project_root, path)
        if not file_path.exists():
            continue
        line_count = len(
            file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        )
        result.append({"path": path, "line_count": line_count})
    return result


def load_target_units(
    project_root: Path, unit_specs: list[dict[str, Any]]
) -> list[TargetUnit]:
    """Load target-unit code excerpts from project-relative unit specs."""

    units = []
    for spec in unit_specs:
        filepath = str(spec.get("filepath") or spec.get("file") or "")
        text = safe_project_path(project_root, filepath).read_text(
            encoding="utf-8",
            errors="replace",
        )
        start_line = int(spec.get("start_line", 1))
        end_line = int(spec.get("end_line", start_line))
        kind = str(spec.get("kind") or "function")
        qualname = str(spec.get("qualname") or "<unit>")
        units.append(
            TargetUnit(
                unit_id=str(
                    spec.get("unit_id")
                    or unit_id(filepath, qualname, start_line, end_line, kind)
                ),
                filepath=filepath,
                qualname=qualname,
                kind=kind,
                start_line=start_line,
                end_line=end_line,
                selection_source=str(spec.get("selection_source") or "case"),
                code=extract_lines(text, start_line, end_line),
            )
        )
    return dedupe_units(units)


def extract_lines(text: str, start_line: int, end_line: int) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    lo = max(1, start_line)
    hi = min(len(lines), end_line)
    return "\n".join(lines[lo - 1 : hi])


def unit_id(
    filepath: str, qualname: str, start_line: int, end_line: int, kind: str
) -> str:
    return f"{filepath}::{qualname}@{start_line}-{end_line}:{kind}"


def dedupe_units(units: list[TargetUnit]) -> list[TargetUnit]:
    files_with_focused_units = {unit.filepath for unit in units if unit.kind != "file"}
    seen: set[str] = set()
    result = []
    for unit in sorted(
        units,
        key=lambda item: (
            item.filepath,
            item.start_line,
            item.end_line,
            item.qualname,
            item.kind,
        ),
    ):
        if unit.kind == "file" and unit.filepath in files_with_focused_units:
            continue
        if unit.unit_id in seen:
            continue
        seen.add(unit.unit_id)
        result.append(unit)
    return result
