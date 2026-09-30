#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from augment.python.models import CodeExcerpt


def safe_relative_path(path: str) -> None:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise SystemExit(f"unsafe relative path: {path}")


def numbered_lines(text: str, *, start_line: int = 1) -> str:
    lines = text.splitlines()
    end_line = start_line + len(lines) - 1
    width = len(str(max(end_line, start_line)))
    return "\n".join(
        f"{line_no:>{width}}: {line}" for line_no, line in enumerate(lines, start_line)
    )


def code_excerpt_from_text(
    path: str,
    text: str,
    *,
    start_line: int = 1,
    end_line: int | None = None,
) -> CodeExcerpt:
    safe_relative_path(path)
    lines = text.splitlines()
    if not lines:
        return CodeExcerpt(path=path, start_line=1, end_line=1, text="")
    end_line = len(lines) if end_line is None else end_line
    lo = max(1, start_line)
    hi = min(len(lines), end_line)
    return CodeExcerpt(
        path=path,
        start_line=lo,
        end_line=hi,
        text=numbered_lines("\n".join(lines[lo - 1 : hi]), start_line=lo),
    )
