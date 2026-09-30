#!/usr/bin/env python3
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from common.failure_context.python import failure_evidence, project_frames
from augment.python.models import ContextRequest
from augment.python.prompt.code_excerpt import code_excerpt_from_text

MAX_CONTEXT_LINES = 90
MAX_TOTAL_CONTEXT_LINES = 320
DEFINITION_KINDS = {"class_definition", "function_definition", "symbol_definition"}


@dataclass(frozen=True)
class RetrievedContext:
    request: dict[str, Any]
    status: str
    path: str = ""
    start_line: int = 0
    end_line: int = 0
    code_excerpt: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DefinitionRecord:
    qualname: str
    kind: str
    path: str
    start_line: int
    end_line: int


class ContextBroker:
    """Resolve model-requested project context with strict path/AST matching."""

    def __init__(self, project_root: Path, source_roots: list[str | Path]) -> None:
        self.project_root = project_root.resolve()
        self.source_roots = [self._resolve_source_root(root) for root in source_roots]
        self.text_by_path: dict[str, str] = {}
        self.definitions_by_path: dict[str, dict[str, list[DefinitionRecord]]] = {}

    def resolve_batch(self, requests: list[ContextRequest]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        remaining = MAX_TOTAL_CONTEXT_LINES
        seen_requests: set[tuple[object, ...]] = set()
        seen_spans: set[tuple[str, int, int]] = set()
        for request in requests:
            request_key = (
                request.kind,
                request.filepath,
                request.qualname,
                request.start_line,
                request.end_line,
            )
            if request_key in seen_requests:
                continue
            seen_requests.add(request_key)
            context = self.resolve(request, line_budget=remaining)
            span = (context.path, context.start_line, context.end_line)
            if context.status == "found" and span in seen_spans:
                continue
            records.append(context.to_dict())
            if context.status == "found":
                seen_spans.add(span)
                remaining -= max(0, context.end_line - context.start_line + 1)
            if remaining <= 0:
                break
        return records

    def resolve(
        self, request: ContextRequest, *, line_budget: int = MAX_CONTEXT_LINES
    ) -> RetrievedContext:
        invalid = invalid_request_note(request)
        if invalid:
            return RetrievedContext(
                request=request.to_dict(), status="invalid", note=invalid
            )
        if request.kind == "module_context":
            return self._module_context(request, line_budget=line_budget)
        if request.kind in DEFINITION_KINDS:
            return self._definition_context(request, line_budget=line_budget)
        return RetrievedContext(
            request=request.to_dict(),
            status="unsupported",
            note=f"unsupported request kind: {request.kind}",
        )

    def resolve_frame(
        self,
        path: str,
        line: int,
        function: str = "",
        *,
        line_budget: int = MAX_CONTEXT_LINES,
    ) -> RetrievedContext:
        request = ContextRequest(
            kind="module_context",
            filepath=path,
            qualname=function if function != "<module>" else "",
            reason=f"traceback frame at {path}:{line}"
            + (f" in {function}" if function else ""),
        )
        text = self._text(path)
        if text is None:
            return RetrievedContext(request=request.to_dict(), status="not_found")
        record = self._frame_definition(path, line)
        if record:
            return context_for_frame(
                request,
                record,
                text,
                line=line,
                line_budget=line_budget,
            )
        start, end = bounded_span(
            len(text.splitlines()), line, line, context=8, line_budget=line_budget
        )
        return found_context(request, path, text, start, end)

    def _module_context(
        self, request: ContextRequest, *, line_budget: int
    ) -> RetrievedContext:
        relpath = normalized_request_path(request.filepath)
        text = self._text(relpath)
        if text is None:
            return RetrievedContext(request=request.to_dict(), status="not_found")
        line_count = len(text.splitlines())
        start = request.start_line or 1
        requested_end = request.end_line or start + MAX_CONTEXT_LINES - 1
        if requested_end < start:
            return RetrievedContext(
                request=request.to_dict(),
                status="invalid",
                note="module context end_line precedes start_line",
            )
        if start > line_count:
            return RetrievedContext(request=request.to_dict(), status="not_found")
        budget = max(1, min(MAX_CONTEXT_LINES, line_budget or MAX_CONTEXT_LINES))
        end = min(line_count, requested_end, start + budget - 1)
        return found_context(request, relpath, text, start, end)

    def _definition_context(
        self, request: ContextRequest, *, line_budget: int
    ) -> RetrievedContext:
        relpath = normalized_request_path(request.filepath)
        text = self._text(relpath)
        if text is None:
            return RetrievedContext(request=request.to_dict(), status="not_found")
        qualname = request.qualname.strip()
        if not qualname:
            return RetrievedContext(
                request=request.to_dict(),
                status="invalid",
                note="definition request missing qualname",
            )
        if (
            request.start_line is not None
            and request.end_line is not None
            and request.end_line < request.start_line
        ):
            return RetrievedContext(
                request=request.to_dict(),
                status="invalid",
                note="definition context end_line precedes start_line",
            )
        candidates = self.definitions_by_path.get(relpath, {}).get(qualname, [])
        if request.kind == "class_definition":
            candidates = [record for record in candidates if record.kind == "class"]
        elif request.kind == "function_definition":
            candidates = [record for record in candidates if record.kind == "function"]
        if request.start_line is not None and request.end_line is not None:
            candidates = [
                record
                for record in candidates
                if record.end_line >= request.start_line
                and record.start_line <= request.end_line
            ]
        elif request.start_line is not None:
            candidates = [
                record
                for record in candidates
                if record.start_line <= request.start_line <= record.end_line
            ]
        elif request.end_line is not None:
            candidates = [
                record
                for record in candidates
                if record.start_line <= request.end_line <= record.end_line
            ]
        if not candidates:
            return RetrievedContext(request=request.to_dict(), status="not_found")
        candidates.sort(key=lambda item: (item.start_line, item.end_line, item.kind))
        if len(candidates) > 1:
            spans = ", ".join(
                f"{record.start_line}-{record.end_line}" for record in candidates
            )
            return RetrievedContext(
                request=request.to_dict(),
                status="ambiguous",
                path=relpath,
                note=f"multiple exact qualname matches at lines {spans}",
            )
        return context_for_record(request, candidates[0], text, line_budget=line_budget)

    def _frame_definition(self, relpath: str, line: int) -> DefinitionRecord | None:
        """Return the innermost definition containing the traceback line.

        Match by path and line rather than the frame's function name.
        """

        records = [
            record
            for by_qualname in self.definitions_by_path.get(relpath, {}).values()
            for record in by_qualname
            if record.start_line <= line <= record.end_line
        ]
        if not records:
            return None
        return min(
            records,
            key=lambda item: (
                item.end_line - item.start_line,
                -item.start_line,
                item.qualname,
            ),
        )

    def _resolve_source_root(self, root: str | Path) -> Path:
        path = Path(root)
        if not path.is_absolute():
            path = self.project_root / path
        path = path.resolve()
        try:
            path.relative_to(self.project_root)
        except ValueError as exc:
            raise SystemExit(f"context source root outside project: {root}") from exc
        return path

    def _text(self, relpath: str) -> str | None:
        """Load one explicitly requested Python source file on demand."""

        if not relpath or Path(relpath).suffix != ".py":
            return None
        if relpath in self.text_by_path:
            return self.text_by_path[relpath]
        path = (self.project_root / relpath).resolve()
        try:
            path.relative_to(self.project_root)
        except ValueError:
            return None
        if not any(path.is_relative_to(root) for root in self.source_roots):
            return None
        if not path.is_file():
            return None
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        self.text_by_path[relpath] = text
        self.definitions_by_path[relpath] = definitions_for_file(relpath, text)
        return text


def context_for_record(
    request: ContextRequest,
    record: DefinitionRecord,
    text: str,
    *,
    line_budget: int,
) -> RetrievedContext:
    start, end = bounded_span(
        len(text.splitlines()),
        record.start_line,
        record.end_line,
        context=1,
        line_budget=line_budget,
    )
    return found_context(request, record.path, text, start, end)


def context_for_frame(
    request: ContextRequest,
    record: DefinitionRecord,
    text: str,
    *,
    line: int,
    line_budget: int,
) -> RetrievedContext:
    """Return definition-bounded context that always includes the failing line."""

    budget = max(1, min(MAX_CONTEXT_LINES, line_budget or MAX_CONTEXT_LINES))
    lo = max(record.start_line, line - budget // 2)
    hi = min(record.end_line, lo + budget - 1)
    lo = max(record.start_line, hi - budget + 1)
    return found_context(request, record.path, text, lo, hi)


def found_context(
    request: ContextRequest, path: str, text: str, start: int, end: int
) -> RetrievedContext:
    """Format a resolved span using the excerpt's effective line boundaries."""
    excerpt = code_excerpt_from_text(path, text, start_line=start, end_line=end)
    return RetrievedContext(
        request=request.to_dict(),
        status="found",
        path=path,
        start_line=excerpt.start_line,
        end_line=excerpt.end_line,
        code_excerpt=excerpt.text,
    )


def definitions_for_file(path: str, text: str) -> dict[str, list[DefinitionRecord]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    visitor = DefinitionVisitor(path)
    visitor.visit(tree)
    result: dict[str, list[DefinitionRecord]] = {}
    for record in visitor.records:
        result.setdefault(record.qualname, []).append(record)
    return result


class DefinitionVisitor(ast.NodeVisitor):
    def __init__(self, path: str) -> None:
        self.path = path
        self.stack: list[str] = []
        self.records: list[DefinitionRecord] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_definition(node, "class")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_definition(node, "function")

    visit_AsyncFunctionDef = visit_FunctionDef

    def _visit_definition(self, node: ast.AST, kind: str) -> None:
        self._record(node, kind)
        self.stack.append(node.name)
        for child in node.body:
            self.visit(child)
        self.stack.pop()

    def _record(self, node: ast.AST, kind: str) -> None:
        name = str(getattr(node, "name", ""))
        qualname = ".".join([*self.stack, name])
        decorators = getattr(node, "decorator_list", [])
        start_line = min(
            [
                int(getattr(node, "lineno", 0)),
                *(int(item.lineno) for item in decorators),
            ]
        )
        self.records.append(
            DefinitionRecord(
                qualname=qualname,
                kind=kind,
                path=self.path,
                start_line=start_line,
                end_line=int(getattr(node, "end_lineno", getattr(node, "lineno", 0))),
            )
        )


def project_traceback_context(
    failure_text: str, broker: ContextBroker
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    frames = project_frames(
        failure_text,
        project_root=broker.project_root,
        source_roots=broker.source_roots,
        max_frames=3,
    )
    for frame in frames:
        contexts.append(
            broker.resolve_frame(
                frame.filepath,
                frame.line,
                frame.function,
            ).to_dict()
        )
    return contexts


def failure_text_from_row(row: dict[str, Any]) -> str:
    parts = [str(row.get("error") or "")]
    for item in row.get("rejected_nodeids", []):
        if isinstance(item, dict):
            parts.append(str(item.get("failure_output") or ""))
            parts.append(str(item.get("output_tail") or ""))
    parts.append(str(row.get("failure_output") or ""))
    return failure_evidence(parts, max_chars=20_000)


def source_roots_from_coverage_source(
    project_root: Path, coverage_source: str
) -> list[str]:
    roots: list[str] = []
    for item in str(coverage_source or "").split(","):
        value = item.strip()
        if value and (project_root / value).exists():
            roots.append(value)
    return roots


def omit_visible_context(
    records: list[dict[str, Any]], visible: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Remove resolved spans already present in the model-visible packet."""

    visible_lines: dict[str, set[int]] = {}
    for item in visible:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "")
        start = int(item.get("start_line") or 0)
        end = int(item.get("end_line") or 0)
        if path and 0 < start <= end:
            visible_lines.setdefault(path, set()).update(range(start, end + 1))

    result: list[dict[str, Any]] = []
    for item in records:
        path = str(item.get("path") or "")
        start = int(item.get("start_line") or 0)
        end = int(item.get("end_line") or 0)
        if (
            item.get("status") == "found"
            and path
            and 0 < start <= end
            and set(range(start, end + 1)).issubset(visible_lines.get(path, set()))
        ):
            continue
        result.append(item)
    return result


def invalid_request_note(request: ContextRequest) -> str:
    if not request.kind.strip():
        return "missing kind"
    if not request.filepath.strip():
        return "missing filepath"
    if normalized_request_path(request.filepath) != request.filepath.strip():
        return f"unsafe filepath: {request.filepath}"
    return ""


def normalized_request_path(path: str) -> str:
    candidate = Path(path.strip())
    if candidate.is_absolute() or ".." in candidate.parts:
        return ""
    return candidate.as_posix()


def bounded_span(
    line_count: int, start_line: int, end_line: int, *, context: int, line_budget: int
) -> tuple[int, int]:
    lo = max(1, start_line - context)
    hi = min(line_count, end_line + context)
    budget = max(1, min(MAX_CONTEXT_LINES, line_budget or MAX_CONTEXT_LINES))
    if hi - lo + 1 <= budget:
        return lo, hi
    return lo, min(line_count, lo + budget - 1)
