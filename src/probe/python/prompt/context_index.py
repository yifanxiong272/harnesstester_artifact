#!/usr/bin/env python3
"""Resolve bounded buggy-side context by exact paths and AST qualnames."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common.failure_context.python import failure_evidence, project_frames
from common.utils.python.paths import safe_project_path, safe_relative_path
from probe.python.input.module_contracts import declaration_names, read_module
from probe.python.prompt.proposal import (
    SUPPORTED_CONTEXT_REQUEST_KINDS as SUPPORTED_REQUEST_KINDS,
)


@dataclass(frozen=True)
class IndexedSymbol:
    qualname: str
    start_line: int
    end_line: int


def failure_text_from_summary(
    summary: dict[str, Any], *, max_chars: int = 20_000
) -> str:
    """Combine retained failure evidence for traceback parsing."""

    diagnostics = summary.get("diagnostics")
    return failure_evidence(
        [
            str(summary.get("failure_excerpt") or ""),
            json.dumps(diagnostics, ensure_ascii=False) if diagnostics else "",
            str(summary.get("output_tail") or ""),
        ],
        max_chars=max_chars,
    )


def resolve_context_requests(
    *,
    project_root: Path,
    source_roots: list[str],
    requests: list[dict[str, Any]],
    max_requests: int = 1,
    max_total_lines: int = 220,
    max_module_lines: int = 90,
    source: str = "buggy-side exact context requests",
) -> dict[str, Any]:
    """Resolve a bounded list of exact context requests."""

    selected_requests = requests[:max_requests]
    index = build_context_index(
        project_root,
        source_roots,
        filepaths=[str(request.get("filepath") or "") for request in selected_requests],
    )
    remaining = max_total_lines
    responses = []
    for request in selected_requests:
        resolved = resolve_context_request(
            project_root=project_root,
            source_roots=source_roots,
            index=index,
            request=request,
            max_lines=min(max_module_lines, max(0, remaining)),
        )
        line_count = int(resolved.get("line_count") or 0)
        remaining = max(0, remaining - line_count)
        responses.append(resolved)
    return {
        "source": source,
        "max_requests": max_requests,
        "max_total_lines": max_total_lines,
        "requests": responses,
    }


def resolve_context_request(
    *,
    project_root: Path,
    source_roots: list[str],
    index: dict[tuple[str, str, str], IndexedSymbol],
    request: dict[str, Any],
    max_lines: int,
) -> dict[str, Any]:
    """Resolve one exact filepath/qualname request against the source index."""

    kind = str(request.get("kind") or "").strip()
    qualname = str(request.get("qualname") or "").strip()
    base = {
        "kind": kind,
        "filepath": str(request.get("filepath") or "").strip(),
        "qualname": qualname,
        "reason": str(request.get("reason") or "").strip(),
    }
    try:
        filepath = normalize_relpath(base["filepath"])
    except SystemExit:
        return {**base, "status": "invalid"}
    base["filepath"] = filepath
    if kind not in SUPPORTED_REQUEST_KINDS:
        return {**base, "status": "unsupported"}
    if not filepath or not path_allowed(filepath, source_roots):
        return {**base, "status": "invalid"}
    try:
        path = safe_project_path(project_root, filepath)
    except SystemExit:
        return {**base, "status": "invalid"}
    if not path.is_file():
        return {**base, "status": "not_found"}
    if kind == "module_context":
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        count = min(max_lines, len(lines))
        return {
            **base,
            "status": "found",
            "start_line": 1,
            "end_line": count,
            "line_count": count,
            "code": numbered_excerpt(lines, start_line=1, max_lines=max_lines),
        }
    if not qualname:
        return {**base, "status": "invalid"}
    symbol = index.get((filepath, qualname, kind))
    if symbol is None:
        return {**base, "status": "not_found"}
    return {
        **base,
        "status": "found",
        **symbol_excerpt(path, symbol, max_lines),
    }


def build_context_index(
    project_root: Path,
    source_roots: list[str],
    *,
    filepaths: list[str],
) -> dict[tuple[str, str, str], IndexedSymbol]:
    """Index symbols only in exact requested or traceback-referenced files."""

    paths = set()
    for rel in filepaths:
        try:
            normalized = normalize_relpath(rel)
        except SystemExit:
            continue
        if normalized and path_allowed(normalized, source_roots):
            paths.add(normalized)

    index: dict[tuple[str, str, str], IndexedSymbol] = {}
    for normalized in sorted(paths):
        try:
            path = safe_project_path(project_root, normalized)
        except SystemExit:
            continue
        if not path.is_file() or path.suffix != ".py":
            continue
        _, tree = read_module(path)
        if tree is None:
            continue
        add_module_symbols(index, normalized, tree.body, parents=[])
    return index


def add_module_symbols(
    index: dict[tuple[str, str, str], IndexedSymbol],
    filepath: str,
    body: list[ast.stmt],
    *,
    parents: list[str],
) -> None:
    for node in body:
        for name, kind in declaration_names(node):
            if kind == "import":
                continue
            kind = "symbol" if kind == "variable" else kind
            qualname = ".".join([*parents, name])
            start = int(getattr(node, "lineno", 0) or 0)
            end = int(getattr(node, "end_lineno", start) or start)
            if start:
                index[(filepath, qualname, f"{kind}_definition")] = IndexedSymbol(
                    qualname, start, end
                )
            if kind in {"class", "function"}:
                add_module_symbols(index, filepath, node.body, parents=[*parents, name])


def project_traceback_context(
    *,
    project_root: Path,
    source_roots: list[str],
    failure_text: str,
    max_frames: int = 3,
    max_lines: int = 90,
) -> list[dict[str, Any]]:
    """Extract bounded source context for project frames in a failure traceback."""

    frames = project_frames(
        failure_text,
        project_root=project_root,
        source_roots=source_roots,
        max_frames=max_frames,
    )
    index = build_context_index(
        project_root,
        source_roots,
        filepaths=[frame.filepath for frame in frames],
    )
    contexts: list[dict[str, Any]] = []
    for trace in frames:
        context = traceback_frame_context(
            project_root,
            index,
            trace.filepath,
            trace.line,
            trace.function,
            max_lines=max_lines,
        )
        if context.get("status") == "found":
            contexts.append(context)
    return contexts


def traceback_frame_context(
    project_root: Path,
    index: dict[tuple[str, str, str], IndexedSymbol],
    filepath: str,
    line: int,
    function: str,
    *,
    max_lines: int,
) -> dict[str, Any]:
    """Return the enclosing symbol or a small line window for one frame."""

    base = {
        "kind": "traceback_frame",
        "filepath": filepath,
        "qualname": "" if function == "<module>" else function,
        "reason": f"buggy validation traceback at {filepath}:{line}",
    }
    try:
        path = safe_project_path(project_root, filepath)
    except SystemExit:
        return {**base, "status": "invalid"}
    if not path.is_file():
        return {**base, "status": "not_found"}
    symbol = enclosing_symbol(index, filepath, line, function)
    if symbol is not None:
        start, end = symbol.start_line, symbol.end_line
    else:
        start, end = max(1, line - 8), line + 8
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if max_lines > 0 and start + max_lines <= line <= min(end, len(lines)):
        start = max(start, min(line - max_lines // 2, end - max_lines + 1))
    code = numbered_excerpt(
        lines, start_line=start, max_lines=max_lines, end_line=end
    )
    return {
        **base,
        "status": "found",
        "start_line": start,
        "end_line": min(end, len(lines), start + max_lines - 1),
        "line_count": len(code.splitlines()),
        "code": code,
    }


def enclosing_symbol(
    index: dict[tuple[str, str, str], IndexedSymbol],
    filepath: str,
    line: int,
    function: str,
) -> IndexedSymbol | None:
    candidates = [
        symbol
        for (path, _qualname, kind), symbol in index.items()
        if path == filepath
        and kind in {"class_definition", "function_definition"}
        and symbol.start_line <= line <= symbol.end_line
    ]
    if function and function != "<module>":
        matches = [
            symbol
            for symbol in candidates
            if symbol.qualname == function or symbol.qualname.endswith(f".{function}")
        ]
        if matches:
            candidates = matches
    if not candidates:
        return None
    return sorted(
        candidates, key=lambda item: (item.start_line, item.end_line, item.qualname)
    )[-1]


def normalize_relpath(path: str) -> str:
    path = path.strip()
    if not path:
        return ""
    safe_relative_path(path)
    return Path(path).as_posix()


def path_allowed(filepath: str, source_roots: list[str]) -> bool:
    path = Path(filepath)
    return any(
        path == Path(root) or Path(root) in path.parents for root in source_roots
    )


def symbol_excerpt(path: Path, symbol: IndexedSymbol, max_lines: int) -> dict[str, Any]:
    end = min(symbol.end_line, symbol.start_line + max_lines - 1)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return {
        "start_line": symbol.start_line,
        "end_line": end,
        "line_count": max(0, end - symbol.start_line + 1),
        "code": numbered_excerpt(
            lines,
            start_line=symbol.start_line,
            end_line=symbol.end_line,
            max_lines=max_lines,
        ),
    }


def numbered_excerpt(
    lines: list[str],
    *,
    start_line: int,
    max_lines: int,
    end_line: int | None = None,
) -> str:
    if max_lines <= 0:
        return ""
    lo = max(1, start_line)
    hi = min(
        len(lines),
        end_line if end_line is not None else lo + max_lines - 1,
        lo + max_lines - 1,
    )
    width = len(str(max(hi, lo)))
    return "\n".join(
        f"{line_no:>{width}}: {lines[line_no - 1]}" for line_no in range(lo, hi + 1)
    )
