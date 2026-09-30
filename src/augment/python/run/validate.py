#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from augment.python.process import start_process, terminate_process_tree
from augment.python.security import sensitive_env_key

ISOLATED_ENV_KEYS = {
    "COVERAGE_FILE",
    "COVERAGE_PROCESS_START",
    "PYTHONHOME",
    "PYTHONPATH",
    "PYTEST_ADDOPTS",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTEST_PLUGINS",
}


def build_env(copy_root: Path, pythonpath: list[str] | None = None) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ISOLATED_ENV_KEYS
        and not key.startswith("COV_CORE_")
        and not sensitive_env_key(key)
    }
    paths = [str(path_for_pythonpath(copy_root, item)) for item in pythonpath or []]
    paths.append(str(copy_root))
    env["PYTHONPATH"] = os.pathsep.join(paths)
    home = copy_root / ".test_augment_home"
    (home / ".config").mkdir(parents=True, exist_ok=True)
    (home / ".cache").mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / ".config")
    env["XDG_CACHE_HOME"] = str(home / ".cache")
    return env


def path_for_pythonpath(copy_root: Path, value: str) -> Path:
    """Resolve relative import paths against the runtime copy; preserve absolute paths."""

    path = Path(value)
    return path if path.is_absolute() else copy_root / path


def run_command(
    cmd: list[str],
    *,
    cwd: Path,
    timeout: int,
    env: dict[str, str] | None = None,
    keep_output: bool = False,
) -> dict[str, Any]:
    """Run one bounded validation command and retain only auditable output."""

    proc = start_process(
        cmd,
        cwd=cwd,
        env=env if env is not None else build_env(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    timed_out = False
    try:
        output, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
    finally:
        original_error = sys.exc_info()[1]
        try:
            try:
                terminate_process_tree(proc, force=timed_out)
                if timed_out:
                    output, _ = proc.communicate(timeout=1)
            finally:
                if proc.stdout is not None:
                    proc.stdout.close()
        except BaseException:
            # Preserve the original read failure or interrupt.
            if original_error is None:
                raise
    output = output or ""
    return {
        "cmd": cmd,
        "exit_code": None if timed_out else proc.returncode,
        "output_tail": output[-8000:],
        **({"timed_out": True} if timed_out else {}),
        **({"output": output} if keep_output else {}),
    }


def collect_nodeids(
    copy_root: Path,
    test_file: str,
    *,
    keyword: str,
    python: str = sys.executable,
    timeout: int = 60,
    pythonpath: list[str] | None = None,
) -> tuple[list[str], dict[str, Any]]:
    """Collect current-round pytest nodeids from the generated test file."""

    env = build_env(copy_root, pythonpath)
    result = run_command(
        [
            python,
            "-m",
            "pytest",
            "-o",
            "addopts=",
            "--rootdir=.",
            "--collect-only",
            "--verbosity=-1",
            test_file,
            "-k",
            keyword,
        ],
        cwd=copy_root,
        env=env,
        timeout=timeout,
        keep_output=True,
    )
    output = str(result.pop("output", result.get("output_tail", "")))
    normalized_file = test_file.replace("\\", "/").removeprefix("./")
    nodeids = []
    for line in output.splitlines():
        value = line.strip()
        if "::" not in value:
            continue
        collected_file = value.split("::", 1)[0].replace("\\", "/").removeprefix("./")
        if collected_file == normalized_file:
            nodeids.append(value)
    return sorted(set(nodeids)), result


def filter_passing_nodeids(
    copy_root: Path,
    nodeids: list[str],
    *,
    python: str = sys.executable,
    timeout: int = 90,
    pythonpath: list[str] | None = None,
) -> dict[str, Any]:
    """Run each generated nodeid independently and partition pass/fail results."""

    env = build_env(copy_root, pythonpath)
    accepted: list[str] = []
    rejected: list[dict[str, Any]] = []
    for nodeid in nodeids:
        result = run_command(
            [
                python,
                "-m",
                "pytest",
                "-o",
                "addopts=",
                "--rootdir=.",
                "-q",
                nodeid,
                "--tb=long",
            ],
            cwd=copy_root,
            env=env,
            timeout=timeout,
            keep_output=True,
        )
        if result.get("exit_code") == 0:
            accepted.append(nodeid)
        else:
            output = str(result.pop("output", ""))
            if output:
                result["failure_output"] = output[-20_000:]
            rejected.append({"nodeid": nodeid, **result})
    return {
        "generated_nodeids": nodeids,
        "accepted_nodeids": accepted,
        "rejected_nodeids": rejected,
    }


def run_coverage_for_nodeids(
    copy_root: Path,
    selectors: list[str],
    out_path: Path,
    *,
    source: str,
    python: str = sys.executable,
    timeout: int = 240,
    pythonpath: list[str] | None = None,
    fail_fast: bool = False,
) -> dict[str, Any]:
    """Measure branch coverage for generated pytest selectors as a set."""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    data_file = out_path.with_suffix(".coverage")
    # A retried attempt must never accept reports left by an interrupted command.
    out_path.unlink(missing_ok=True)
    data_file.unlink(missing_ok=True)
    env = build_env(copy_root, pythonpath)
    try:
        run = run_command(
            [
                python,
                "-m",
                "coverage",
                "run",
                "--branch",
                f"--source={source}",
                "--data-file",
                str(data_file),
                "-m",
                "pytest",
                "-o",
                "addopts=",
                "--rootdir=.",
                "-q",
                *(["-x"] if fail_fast else []),
                *selectors,
            ],
            cwd=copy_root,
            env=env,
            timeout=timeout,
        )
        if run.get("exit_code") != 0:
            return {"coverage_run": run, "coverage_json": None}
        dump = run_command(
            [
                python,
                "-m",
                "coverage",
                "json",
                "--fail-under=0",
                "--data-file",
                str(data_file),
                "-o",
                str(out_path),
            ],
            cwd=copy_root,
            env=env,
            timeout=timeout,
        )
        if dump.get("exit_code") != 0:
            out_path.unlink(missing_ok=True)
        return {
            "coverage_run": run,
            "coverage_json": dump,
            "coverage_path": str(out_path),
        }
    finally:
        data_file.unlink(missing_ok=True)


def coverage_succeeded(result: dict[str, Any], out_path: Path) -> bool:
    """Return whether coverage execution and JSON export both completed."""

    run = result.get("coverage_run")
    dump = result.get("coverage_json")
    return (
        isinstance(run, dict)
        and run.get("exit_code") == 0
        and isinstance(dump, dict)
        and dump.get("exit_code") == 0
        and out_path.is_file()
    )
