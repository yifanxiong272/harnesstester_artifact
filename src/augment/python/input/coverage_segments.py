#!/usr/bin/env python3
from __future__ import annotations

import ast
import copy
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SEGMENT_LINE_LIMIT = 50


@dataclass(frozen=True)
class FileCoverage:
    """Normalized line and branch facts used to segment one source file."""

    missing_lines: frozenset[int]
    covered_lines: frozenset[int]
    missing_branches: frozenset[tuple[int, int]]
    covered_branches: frozenset[tuple[int, int]]

    @property
    def lines_of_interest(self) -> set[int]:
        lines = set(self.missing_lines)
        for source, destination in self.missing_branches:
            if source > 0:
                lines.add(source)
            if destination > 0:
                lines.add(destination)
        return lines


@dataclass(frozen=True)
class SegmentDefinition:
    """One non-overlapping AST definition selected for coverage generation."""

    node: ast.AST
    start_line: int
    stop_line: int
    context_ranges: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class SegmentBuildContext:
    """File-level facts shared while serializing selected AST definitions."""

    filepath: str
    coverage: FileCoverage
    qualnames: dict[int, str]


def build_segment_manifest(
    project_root: Path,
    snapshot: dict[str, Any],
    *,
    line_limit: int = SEGMENT_LINE_LIMIT,
) -> dict[str, Any]:
    """Build the immutable file-scoped queue from round-zero coverage.

    Frozen LDH facts select the source-file scope. Ordinary coverage and Python
    AST ranges then construct CoverUp-compatible segments, globally ordered by
    missing line-plus-branch count.
    """

    coverage_files = snapshot.get("general_coverage", {}).get("files", {})
    if not isinstance(coverage_files, dict):
        raise SystemExit("metric snapshot general_coverage.files must be an object")
    allowlist = ldh_file_scope(snapshot)

    segments: list[dict[str, Any]] = []
    for filepath in allowlist:
        coverage = coverage_files[filepath]
        file_segments = segments_for_file(
            project_root,
            filepath,
            coverage,
            line_limit=line_limit,
        )
        segments.extend(file_segments)

    # Python's stable sort preserves CoverUp's coverage-file and AST discovery
    # order when two segments have the same missing-count priority.
    segments.sort(
        key=lambda item: int(item["segment"]["missing_count"]),
        reverse=True,
    )
    return {"segments": segments}


def ldh_file_scope(snapshot: dict[str, Any]) -> list[str]:
    """Return measurable LDH-bearing files in ordinary coverage order."""

    coverage_files = snapshot.get("general_coverage", {}).get("files", {})
    ldh_files = snapshot.get("ldh_coverage", {}).get("files", {})
    if not isinstance(coverage_files, dict):
        raise SystemExit("metric snapshot general_coverage.files must be an object")
    if not isinstance(ldh_files, dict):
        raise SystemExit("metric snapshot ldh_coverage.files must be an object")
    files = [filepath for filepath in coverage_files if filepath in ldh_files]
    missing = set(ldh_files).difference(files)
    if missing:
        raise SystemExit(
            "ordinary coverage is missing LDH source files: "
            + ", ".join(sorted(missing))
        )
    return files


def residual_segment(
    objective: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any] | None:
    """Project one fixed segment onto the current ordinary coverage gap.

    The manifest keeps round-zero gaps for stable ranking and reproducibility.
    Before generation, the workflow intersects those gaps with the current
    snapshot so a test is measured only against locations that remain missing
    at the start of this round.
    """

    initial = objective.get("general_coverage", {})
    if not isinstance(initial, dict):
        raise SystemExit("coverage segment is missing general_coverage")
    lines, branches = segment_residual_gap(objective, snapshot)
    if not lines and not branches:
        return None

    projected = copy.deepcopy(objective)
    projected["general_coverage"] = {
        **initial,
        "uncovered_lines": lines,
        "uncovered_branches": [arc_key(arc) for arc in branches],
        "covered_lines": max(0, int(initial.get("total_lines") or 0) - len(lines)),
        "covered_branches": max(
            0, int(initial.get("total_branches") or 0) - len(branches)
        ),
    }
    return projected


def next_residual_segment(
    objectives: list[dict[str, Any]],
    snapshot: dict[str, Any],
    *,
    start: int,
) -> tuple[dict[str, Any] | None, int, list[str]]:
    """Return the next unresolved segment without changing the fixed order.

    Fully covered entries advance the queue cursor but do not consume a model
    generation round. The returned cursor always points after the selected
    segment, or to the end of the queue when no residual target remains.
    """

    skipped: list[str] = []
    for index in range(start, len(objectives)):
        objective = residual_segment(objectives[index], snapshot)
        if objective is not None:
            return objective, index + 1, skipped
        skipped.append(str(objectives[index].get("objective_id") or ""))
    return None, len(objectives), skipped


def segment_residual_gap(
    objective: dict[str, Any],
    snapshot: dict[str, Any],
) -> tuple[list[int], list[tuple[int, int]]]:
    """Return current missing locations that belonged to the initial segment."""

    filepath = str(objective.get("filepath") or "")
    initial = objective.get("general_coverage", {})
    if not isinstance(initial, dict):
        raise SystemExit("coverage segment is missing general_coverage")
    current = snapshot.get("general_coverage", {}).get("files", {}).get(filepath)
    if not isinstance(current, dict):
        raise SystemExit(
            f"current general coverage is missing segment file: {filepath}"
        )
    lines = sorted(
        positive_ints(initial.get("uncovered_lines", []))
        & positive_ints(current.get("uncovered_lines", []))
    )
    branches = sorted(
        branch_arcs(initial.get("uncovered_branches", []))
        & branch_arcs(current.get("uncovered_branches", []))
    )
    return lines, branches


def segments_for_file(
    project_root: Path,
    filepath: str,
    coverage: dict[str, Any],
    *,
    line_limit: int,
) -> list[dict[str, Any]]:
    """Return non-overlapping AST coverage segments for one Python file."""

    path = project_source_path(project_root, filepath)
    text = path.read_text(encoding="utf-8", errors="replace")
    tree = parse_source(text, filepath)
    facts = file_coverage(coverage)
    build_context = SegmentBuildContext(
        filepath=filepath,
        coverage=facts,
        qualnames=definition_qualnames(tree),
    )
    return [
        payload
        for definition in segment_definitions(
            tree, facts.lines_of_interest, line_limit=line_limit
        )
        if (payload := segment_payload(build_context, definition)) is not None
    ]


def parse_source(text: str, filepath: str) -> ast.Module:
    """Parse one measured Python source file or report the exact syntax error."""

    try:
        return ast.parse(text, filename=filepath)
    except SyntaxError as exc:
        raise SystemExit(
            f"cannot parse coverage source file: {filepath}: {exc}"
        ) from exc


def file_coverage(coverage: dict[str, Any]) -> FileCoverage:
    """Normalize one file's ordinary coverage facts."""

    return FileCoverage(
        missing_lines=frozenset(positive_ints(coverage.get("uncovered_lines", []))),
        covered_lines=frozenset(positive_ints(coverage.get("covered_lines", []))),
        missing_branches=frozenset(branch_arcs(coverage.get("uncovered_branches", []))),
        covered_branches=frozenset(branch_arcs(coverage.get("covered_branches", []))),
    )


def segment_definitions(
    tree: ast.Module,
    lines_of_interest: set[int],
    *,
    line_limit: int,
) -> list[SegmentDefinition]:
    """Select CoverUp-compatible, non-overlapping enclosing definitions."""

    definitions: list[SegmentDefinition] = []
    claimed_lines: set[int] = set()
    for line in sorted(lines_of_interest):
        if line in claimed_lines:
            continue
        enclosing = find_enclosing(tree, line)
        if enclosing is None:
            continue
        node, begin, end = enclosing
        context: list[tuple[int, int]] = []
        while isinstance(node, ast.ClassDef) and end - begin > line_limit:
            nested = find_enclosing(node, line)
            if nested is None:
                break
            context.append((begin, int(node.lineno) + 1))
            node, begin, end = nested
        if isinstance(node, ast.ClassDef) and end - begin > line_limit:
            continue
        definitions.append(
            SegmentDefinition(
                node=node,
                start_line=begin,
                stop_line=end,
                context_ranges=tuple(context),
            )
        )
        claimed_lines.update(range(begin, end))
    return definitions


def segment_payload(
    context: SegmentBuildContext,
    definition: SegmentDefinition,
) -> dict[str, Any] | None:
    """Serialize one selected definition using only coverage and AST facts."""

    facts = context.coverage
    start = definition.start_line
    stop = definition.stop_line
    line_range = set(range(start, stop))
    missing_lines = sorted(facts.missing_lines & line_range)
    missing_branches = sorted(
        arc for arc in facts.missing_branches if arc[0] in line_range
    )
    if not missing_lines and not missing_branches:
        return None

    covered_lines = facts.covered_lines & line_range
    covered_branches = {arc for arc in facts.covered_branches if arc[0] in line_range}
    executable_lines = (facts.missing_lines | facts.covered_lines) & line_range
    end_line = stop - 1
    node = definition.node
    qualname = context.qualnames.get(id(node), str(getattr(node, "name", "")))
    segment_id = f"segment:{context.filepath}:{start}:{end_line}"
    return {
        "objective_id": hashlib.sha1(segment_id.encode()).hexdigest()[:12],
        "filepath": context.filepath,
        "start_line": start,
        "end_line": end_line,
        "unit": {
            "unit_id": segment_id,
            "kind": definition_kind(node),
            "filepath": context.filepath,
            "qualname": qualname,
            "start_line": start,
            "end_line": end_line,
        },
        "general_coverage": {
            "uncovered_lines": missing_lines,
            "uncovered_branches": [arc_key(arc) for arc in missing_branches],
            "covered_lines": len(covered_lines),
            "total_lines": len(executable_lines),
            "covered_branches": len(covered_branches),
            "total_branches": len(covered_branches | set(missing_branches)),
        },
        "segment": {
            "context_ranges": [
                {"start_line": begin, "end_line": end - 1}
                for begin, end in definition.context_ranges
            ],
            "missing_count": len(missing_lines) + len(missing_branches),
        },
    }


def find_enclosing(root: ast.AST, line: int) -> tuple[ast.AST, int, int] | None:
    """Return the first enclosing definition in AST walk order, as CoverUp does."""

    for node in ast.walk(root):
        if node is root or not isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        begin = first_line(node)
        end = int(getattr(node, "end_lineno", node.lineno)) + 1
        if begin <= line < end:
            return node, begin, end
    return None


def first_line(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> int:
    return min([int(node.lineno), *(int(item.lineno) for item in node.decorator_list)])


def definition_qualnames(tree: ast.AST) -> dict[int, str]:
    result: dict[int, str] = {}

    def visit(body: list[ast.stmt], scope: list[str]) -> None:
        for node in body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                qualname = ".".join([*scope, node.name])
                result[id(node)] = qualname
                visit(node.body, [*scope, node.name])

    visit(getattr(tree, "body", []), [])
    return result


def definition_kind(node: ast.AST) -> str:
    if isinstance(node, ast.ClassDef):
        return "class"
    if isinstance(node, ast.AsyncFunctionDef):
        return "async_function"
    return "function"


def positive_ints(values: Any) -> set[int]:
    result: set[int] = set()
    for value in values if isinstance(values, list) else ():
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            result.add(parsed)
    return result


def branch_arcs(values: Any) -> set[tuple[int, int]]:
    result: set[tuple[int, int]] = set()
    for value in values if isinstance(values, list) else ():
        if isinstance(value, str):
            source, separator, destination = value.partition("->")
            if not separator:
                continue
            try:
                result.add((int(source), int(destination)))
            except ValueError:
                continue
        elif isinstance(value, list) and len(value) == 2:
            try:
                result.add((int(value[0]), int(value[1])))
            except (TypeError, ValueError):
                continue
    return result


def arc_key(arc: tuple[int, int]) -> str:
    return f"{arc[0]}->{arc[1]}"


def project_source_path(project_root: Path, filepath: str) -> Path:
    """Return one verified project-local source path used by the segment queue."""

    relative = Path(filepath)
    if relative.is_absolute() or ".." in relative.parts:
        raise SystemExit(f"unsafe coverage source path: {filepath}")
    root = project_root.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise SystemExit(
            f"coverage source path escapes project root: {filepath}"
        ) from exc
    if not path.is_file():
        raise SystemExit(f"coverage source file does not exist: {filepath}")
    return path
