#!/usr/bin/env python3
"""Collect branch-enabled pytest coverage for an explicit source-file scope."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def source_paths(root: Path, manifest: Path) -> list[Path]:
    """Read the same explicit file universe used by extraction."""
    data = json.loads(manifest.read_text())
    entries = data.get("files")
    if entries is None:
        entries = [item["file"] for item in data.get("locations", [])]
    if not isinstance(entries, list) or not entries:
        raise ValueError("source_files must contain a nonempty files array")
    files = []
    for entry in entries:
        if not isinstance(entry, str):
            raise ValueError("source_files entries must be paths")
        file = (root / entry).resolve()
        if Path(entry).is_absolute() or not file.is_relative_to(root):
            raise ValueError(f"source path must be checkout-relative: {entry}")
        if file.suffix != ".py" or not file.is_file():
            raise ValueError(f"source must be an existing Python file: {entry}")
        files.append(file)
    if len(set(files)) != len(files):
        raise ValueError("source_files contains duplicate paths")
    return files


def coverage_session(root: Path, files: list[Path], output: Path):
    """Preserve coverage.py exclusion rules while measuring the explicit scope."""
    import coverage

    os.chdir(root)
    cov = coverage.Coverage(data_file=str(output / "raw" / ".coverage"), branch=True)
    cov.set_option("run:source", None)
    cov.set_option("run:source_pkgs", [])
    if hasattr(cov.config, "source_dirs"):
        cov.set_option("run:source_dirs", [])
    cov.set_option("run:relative_files", False)
    cov.set_option("run:include", [str(file) for file in files])
    cov.set_option("run:omit", [])
    cov.set_option("report:include", None)
    cov.set_option("report:omit", None)
    cov.set_option("run:parallel", False)
    cov.set_option("run:sigterm", os.name == "posix")
    return cov


def signal_group(proc: subprocess.Popen, sig: signal.Signals) -> None:
    try:
        if os.name == "posix":
            os.killpg(proc.pid, sig)
        else:
            proc.send_signal(sig)
    except ProcessLookupError:
        pass


def run_tests(command: list[str], root: Path, output: Path, timeout: float) -> dict:
    """Keep execution status independently of whether coverage was saved."""
    started = time.monotonic()
    timed_out = False
    interrupted = False
    with (output / "test.log").open("w") as log:
        proc = subprocess.Popen(command, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=os.name == "posix")
        def interrupt(signum, frame):
            raise KeyboardInterrupt

        previous = signal.signal(signal.SIGTERM, interrupt)
        try:
            proc.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as error:
            timed_out = isinstance(error, subprocess.TimeoutExpired)
            interrupted = not timed_out
            signal_group(proc, signal.SIGTERM)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                signal_group(proc, signal.SIGKILL)
                proc.wait()
        finally:
            signal.signal(signal.SIGTERM, previous)
            if timed_out or interrupted or proc.poll() is None:
                signal_group(proc, signal.SIGKILL)
                proc.wait()
    return {
        "command": command,
        "status": "interrupted" if interrupted else "timeout" if timed_out else ("passed" if proc.returncode == 0 else "failed"),
        "exit_code": proc.returncode,
        "duration_seconds": time.monotonic() - started,
        "log": "test.log",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--source-files", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    root, manifest, output = args.project_root.resolve(), args.source_files.resolve(), args.out_dir.resolve()
    if not root.is_dir() or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("project-root must exist and timeout must be positive")
    files = source_paths(root, manifest)
    tests = args.pytest_args[1:] if args.pytest_args[:1] == ["--"] else args.pytest_args
    if args.worker:
        sys.path.insert(0, str(root))
        cov = coverage_session(root, files, output)
        cov.start()
        try:
            import pytest

            return int(pytest.main(tests))
        finally:
            cov.stop()
            cov.save()

    if output.is_relative_to(root):
        parser.error("out-dir must be outside the checkout")
    output.mkdir(parents=True, exist_ok=False)
    (output / "raw").mkdir()
    command = [sys.executable, str(Path(__file__).resolve()), "--worker",
               "--project-root", str(root), "--source-files", str(manifest),
               "--out-dir", str(output), "--", *tests]
    record = run_tests(command, root, output, args.timeout)
    record["coverage_available"] = (output / "raw" / ".coverage").is_file()
    write_json(output / "run.json", record)
    try:
        if not record["coverage_available"]:
            raise ValueError("test process produced no saved coverage data; see test.log")
        cov = coverage_session(root, files, output)
        cov.load()
        # Empty arcs let coverage.py report genuinely unexecuted source files.
        cov.get_data().add_arcs({str(file): [] for file in files})
        raw = output / "raw" / "coverage.json"
        cov.json_report(morfs=[str(file) for file in files], outfile=str(raw))
        reported = json.loads(raw.read_text())["files"]
        rows = {(root / file).resolve(): value for file, value in reported.items()}
        fields = ("executed_lines", "missing_lines", "executed_branches", "missing_branches")
        result = {"files": {file.relative_to(root).as_posix(): {key: rows[file][key] for key in fields}
                            for file in files}}
        write_json(output / "coverage.json", result)
    except Exception as error:
        record["coverage_error"] = str(error)
        write_json(output / "run.json", record)
        print(str(error), file=sys.stderr)
        return 1
    print(output / "coverage.json")
    return 130 if record["status"] == "interrupted" else 0


if __name__ == "__main__":
    raise SystemExit(main())
