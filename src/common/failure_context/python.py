#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
PYTHON_FRAME_RE = re.compile(r'File "([^"]+)", line (\d+), in ([^\n]+)')
PYTEST_FRAME_RE = re.compile(r"^\s*([^:\n]+\.py):(\d+):\s+in\s+([^\n]+?)\s*$", re.MULTILINE)
PYTEST_LOCATION_RE = re.compile(r"^\s*([^:\n]+\.py):(\d+)(?::\d+)?:", re.MULTILINE)
IMPORT_PATH_RE = re.compile(r"\(([^()\n]+\.py)\)")
EXCLUDED_PARTS = {".venv", "node_modules", "site-packages", "test", "tests", "__pycache__"}


@dataclass(frozen=True)
class FailureFrame:
    raw_path: str
    filepath: str
    line: int
    function: str
    offset: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def failure_evidence(parts: Iterable[object], *, max_chars: int = 20_000) -> str:
    """Return bounded, de-duplicated failure evidence without terminal escapes."""

    values = [str(part) for part in parts if part]
    unique = list(dict.fromkeys(values))
    return ANSI_ESCAPE_RE.sub("", "\n".join(unique))[-max_chars:]


def project_frames(
    text: str,
    *,
    project_root: Path,
    source_roots: Iterable[str | Path],
    max_frames: int = 3,
) -> list[FailureFrame]:
    """Select the innermost unique Python production frames."""

    parsed: list[tuple[int, str, int, str]] = []
    for pattern in (PYTHON_FRAME_RE, PYTEST_FRAME_RE):
        parsed.extend(
            (match.start(), match.group(1), int(match.group(2)), match.group(3).strip())
            for match in pattern.finditer(text)
        )
    parsed.extend(
        (match.start(), match.group(1), int(match.group(2)), "<module>")
        for match in PYTEST_LOCATION_RE.finditer(text)
    )
    # Import errors may identify the resolved module without a source line.
    # Keep these as lowest-priority file-level evidence after real frames.
    parsed.extend(
        (-1, match.group(1), 1, "<module>")
        for match in IMPORT_PATH_RE.finditer(text)
    )
    return _resolved_frames(
        sorted(parsed, key=lambda item: -item[0]),
        project_root=project_root,
        source_roots=source_roots,
        max_frames=max_frames,
    )


def canonical_project_path(
    raw_path: str,
    *,
    project_root: Path,
    source_roots: Iterable[str | Path],
) -> str:
    """Map a real or copied-workspace path to one unambiguous project file."""

    root = project_root.resolve()
    roots = [_source_root(root, item) for item in source_roots]
    normalized = raw_path.replace("\\", "/").removeprefix("file://")
    raw = Path(normalized)
    if raw.is_absolute():
        try:
            direct = raw.resolve().relative_to(root)
        except (OSError, ValueError):
            pass
        else:
            if candidate := _valid_candidate(root, roots, direct):
                return candidate

    candidates: set[str] = set()
    if not raw.is_absolute():
        candidates.add(normalized.removeprefix("./"))
    parts = [part for part in normalized.split("/") if part]
    candidates.update("/".join(parts[index:]) for index in range(len(parts)))
    matches = {
        candidate
        for value in candidates
        if (candidate := _valid_candidate(root, roots, Path(value)))
    }
    return matches.pop() if len(matches) == 1 else ""


def _resolved_frames(
    parsed: Iterable[tuple[int, str, int, str]],
    *,
    project_root: Path,
    source_roots: Iterable[str | Path],
    max_frames: int,
) -> list[FailureFrame]:
    frames: list[FailureFrame] = []
    seen: set[tuple[str, int]] = set()
    for offset, raw_path, line, function in parsed:
        filepath = canonical_project_path(
            raw_path,
            project_root=project_root,
            source_roots=source_roots,
        )
        key = (filepath, line)
        if not filepath or key in seen:
            continue
        seen.add(key)
        frames.append(FailureFrame(raw_path, filepath, line, function, offset))
        if len(frames) >= max_frames:
            break
    return frames


def _source_root(project_root: Path, value: str | Path) -> Path:
    root = Path(value)
    if not root.is_absolute():
        root = project_root / root
    resolved = root.resolve()
    resolved.relative_to(project_root)
    return resolved


def _valid_candidate(project_root: Path, source_roots: list[Path], relative: Path) -> str:
    if relative.is_absolute() or ".." in relative.parts or EXCLUDED_PARTS & set(relative.parts):
        return ""
    candidate = (project_root / relative).resolve()
    try:
        project_relative = candidate.relative_to(project_root)
    except ValueError:
        return ""
    if candidate.suffix != ".py" or not candidate.is_file():
        return ""
    if not any(candidate.is_relative_to(root) for root in source_roots):
        return ""
    return project_relative.as_posix()
