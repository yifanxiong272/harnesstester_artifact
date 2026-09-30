"""Extract the Python LLM-dependent harness (LDH) and write its region outputs."""

from __future__ import annotations

from pathlib import Path

from common.utils.python.json_io import read_json, write_json
from common.utils.python.paths import safe_project_path
from llm_dependent.python.flow import analyze_flow_project_outputs


def load_source_files(project_root: Path, source_base: Path) -> list[Path]:
    """Read a nonempty file list; analysis order is sorted by project path."""
    payload = read_json(source_base)
    entries = payload.get("files") if isinstance(payload, dict) else None
    if (
        entries is None
        and isinstance(payload, dict)
        and isinstance(payload.get("locations"), list)
    ):
        entries = [
            row.get("file") if isinstance(row, dict) else None
            for row in payload["locations"]
        ]
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"{source_base}: expected a nonempty 'files' array")
    files = set()
    for entry in entries:
        if not isinstance(entry, str) or not entry:
            raise ValueError(f"{source_base}: file paths must be nonempty strings")
        path = safe_project_path(project_root, entry)
        if path.suffix != ".py" or not path.is_file():
            raise ValueError(
                f"{source_base}: expected an existing Python file: {entry}"
            )
        if path in files:
            raise ValueError(f"{source_base}: duplicate source file: {entry}")
        files.add(path)
    return sorted(files)


def run_python(
    *,
    project_root: Path,
    source_base: Path,
    project_label: str,
    outputs: dict[str, Path],
) -> Path:
    payloads = analyze_flow_project_outputs(
        project_root=project_root,
        source_files=load_source_files(project_root, source_base),
        project_label=project_label,
        control_modes=("none", "direct", "recursive"),
    )
    for mode, output in outputs.items():
        write_json(output, payloads[mode])
    print(outputs["none"])
    return outputs["none"]
