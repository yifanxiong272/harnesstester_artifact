#!/usr/bin/env python3
"""Run generated pytest assets and extract compact validation evidence."""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from common.utils.python.paths import STUDY_SRC_ROOT
from probe.python.run.deadline import CaseTimeBudgetExceeded, limit_timeout

FAILED_NODE_RE = re.compile(r"^FAILED\s+(\S+)")
VALIDATION_PYTHONPATH_ROOTS_ENV = "TEST_AUGMENT_PYTHONPATH_ROOTS"
PYTEST_REPORT_ENV = "TEST_AUGMENT_PYTEST_REPORT"
PYTEST_REPORT_PLUGIN = "probe.python.runtime.pytest_structured_reporter"
PYTEST_CONFIG_CANDIDATES = ("pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg")
VALIDATION_ENV_KEYS = {
    "COMSPEC",
    "GIT_PYTHON_GIT_EXECUTABLE",
    "LANG",
    "LC_ALL",
    "PATH",
    "PATHEXT",
    "SHELL",
    "SYSTEMROOT",
    "TERM",
    "TZ",
    "WINDIR",
}


def validation_python_paths(copy_root: Path) -> list[str]:
    paths = [copy_root / "src", copy_root]
    for value in os.environ.get(VALIDATION_PYTHONPATH_ROOTS_ENV, "").split(os.pathsep):
        value = value.strip()
        if not value:
            continue
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe validation Python path root: {value}")
        candidate = (copy_root / relative).resolve()
        if not candidate.is_relative_to(copy_root.resolve()):
            raise ValueError(f"validation Python path escapes checkout: {value}")
        if candidate.is_dir():
            paths.append(candidate)
    paths.append(STUDY_SRC_ROOT)
    return [str(path) for path in paths]


def build_test_env(
    copy_root: Path, *, extra_env: dict[str, str] | None = None
) -> dict[str, str]:
    """Build a credential-free environment for executing generated tests."""

    env = {
        key: value for key, value in os.environ.items() if key in VALIDATION_ENV_KEYS
    }
    if extra_env:
        env.update(extra_env)
    paths = validation_python_paths(copy_root)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    home = copy_root / ".test-augment-home"
    temporary = copy_root / ".test-augment-tmp"
    cache = copy_root / ".test-augment-cache"
    for directory in (home, temporary, cache):
        directory.mkdir(parents=True, exist_ok=True)
    env.update(
        {
            "CI": "true",
            "HOME": str(home),
            "NO_COLOR": "1",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": str(temporary),
            "XDG_CACHE_HOME": str(cache),
        }
    )
    return env


def sandbox_path(value: Path | str) -> str:
    path = Path(value).expanduser().resolve()
    return json.dumps(str(path))


def sandbox_ancestor_rules(paths: list[Path]) -> list[str]:
    allowed: set[Path] = set()
    for path in paths:
        current = path.resolve()
        while True:
            allowed.add(current)
            if current.parent == current:
                break
            current = current.parent
    rules = []
    for path in sorted(allowed, key=lambda item: len(str(item))):
        literal = sandbox_path(path)
        rules.extend(
            [
                f"(allow file-read-metadata (literal {literal}))",
                f"(allow file-read-data (literal {literal}))",
            ]
        )
    return rules


def sandboxed_pytest_command(
    command: list[str],
    *,
    copy_root: Path,
    test_file: str,
) -> tuple[list[str], dict[str, Any]]:
    sandbox = Path("/usr/bin/sandbox-exec")
    if sys.platform != "darwin" or not sandbox.exists():
        return command, {"network_sandboxed": False, "filesystem_sandboxed": False}
    executable = Path(shutil.which(command[0]) or command[0]).expanduser()
    lexical_runtime = Path(os.path.abspath(executable)).parent.parent
    resolved_runtime = (
        executable.resolve().parent.parent if executable.exists() else lexical_runtime
    )
    read_roots = [
        copy_root.resolve(),
        (STUDY_SRC_ROOT).resolve(),
        lexical_runtime,
        resolved_runtime,
        Path("/opt/homebrew/Cellar"),
        Path("/opt/homebrew/etc"),
        Path("/opt/homebrew/lib"),
        Path("/opt/homebrew/opt"),
        Path("/usr/local/Cellar"),
        Path("/usr/local/lib"),
        Path("/usr/local/opt"),
        Path("/Library/Developer/CommandLineTools"),
        Path("/System"),
        Path("/usr/lib"),
        Path("/etc/mime.types"),
        Path("/etc/apache2/mime.types"),
    ]
    read_roots = [path for path in read_roots if path.exists()]
    write_roots = [
        (copy_root / Path(test_file).parent).resolve(),
        (copy_root / ".pytest_cache").resolve(),
        (copy_root / ".test-augment-home").resolve(),
        (copy_root / ".test-augment-tmp").resolve(),
        (copy_root / ".test-augment-cache").resolve(),
        (copy_root / ".test-augment-evidence").resolve(),
    ]
    profile = [
        "(version 1)",
        "(allow default)",
        "(deny network*)",
        "(deny file-write*)",
        "(deny file-read-data)",
        *sandbox_ancestor_rules(read_roots),
        *(
            f"(allow file-read-data (subpath {sandbox_path(path)}))"
            for path in read_roots
        ),
        f"(allow file-read-data (literal {sandbox_path('/dev/null')}))",
        f"(allow file-read-data (literal {sandbox_path('/dev/random')}))",
        f"(allow file-read-data (literal {sandbox_path('/dev/urandom')}))",
        *(
            f"(allow file-write* (subpath {sandbox_path(path)}))"
            for path in write_roots
        ),
        f"(allow file-write* (literal {sandbox_path('/dev/null')}))",
        f"(deny file-read-data (literal {sandbox_path(copy_root / '.git')}))",
        f"(deny file-read-data (subpath {sandbox_path(copy_root / '.git')}))",
    ]
    return [str(sandbox), "-p", " ".join(profile), *command], {
        "network_sandboxed": True,
        "loopback_network_allowed": False,
        "unix_socket_roots_allowed": [],
        "filesystem_sandboxed": True,
    }


def pytest_config_for_checkout(copy_root: Path) -> Path:
    for name in PYTEST_CONFIG_CANDIDATES:
        candidate = copy_root / name
        if candidate.is_file():
            return candidate
    return Path("/dev/null")


def run_command(
    cmd: list[str],
    *,
    cwd: Path,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    proc: subprocess.Popen[str] | None = None
    timeout = limit_timeout(timeout)
    timed_out = False
    exit_code = None
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=os.name != "nt",
        )
        output, _ = proc.communicate(timeout=timeout)
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
    except OSError as exc:
        if proc is not None or isinstance(exc, CaseTimeBudgetExceeded):
            raise
        output = str(exc)
        cleanup = {"attempted": False, "reason": "process_not_started"}
    finally:
        original_error = sys.exc_info()[1]
        if proc is not None:
            try:
                try:
                    cleanup = terminate_process_group(proc, force=timed_out)
                    if timed_out:
                        output, _ = proc.communicate(timeout=1)
                finally:
                    if proc.stdout is not None:
                        proc.stdout.close()
            except BaseException:
                # Preserve the original read failure or interrupt.
                if original_error is None:
                    raise
    if proc is not None:
        limit_timeout()
    return {
        "cmd": cmd,
        "cwd": str(cwd),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "output_tail": (output or "")[-8000:],
        "process_group_cleanup": cleanup,
    }


def terminate_process_group(
    proc: subprocess.Popen[str] | None,
    *,
    force: bool = False,
) -> dict[str, Any]:
    if proc is None:
        return {"attempted": False, "reason": "process_not_started"}
    if os.name == "nt":
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=1)
            return {"attempted": True, "signal": "terminate"}
        return {"attempted": False, "reason": "process_exited"}
    sent = None
    try:
        os.killpg(proc.pid, signal.SIGKILL if force else signal.SIGTERM)
        sent = "SIGKILL" if force else "SIGTERM"
        if not force:
            deadline = time.monotonic() + 0.2
            while time.monotonic() < deadline:
                proc.poll()
                os.killpg(proc.pid, 0)
                time.sleep(0.01)
            os.killpg(proc.pid, signal.SIGKILL)
            sent = "SIGKILL"
    except ProcessLookupError:
        pass
    proc.wait(timeout=1)
    return (
        {"attempted": True, "signal": sent}
        if sent
        else {"attempted": False, "reason": "process_group_exited"}
    )


def pytest_evidence(
    output: str,
    exit_code: int | None,
    timed_out: bool,
    *,
    report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a run from structured pytest facts, never exception-name allowlists."""

    if timed_out:
        status = "needs_repair"
        source = "process"
        reason = "timeout"
    elif not report or report.get("schema") != "test-augment-pytest-structured-report":
        status = "needs_repair"
        source = "process"
        reason = "structured_report_unavailable"
    else:
        status, reason = structured_pytest_status(report, exit_code)
        source = "structured_reporter"
    failed_nodeids = {
        str(item["nodeid"])
        for item in (report or {}).get("test_reports", [])
        if isinstance(item, dict)
        and item.get("outcome") == "failed"
        and item.get("nodeid")
    }
    if not failed_nodeids:
        for line in output.splitlines():
            match = FAILED_NODE_RE.match(line.strip())
            if match:
                failed_nodeids.add(match.group(1))
    return {
        "status": status,
        "passed": status == "passed",
        "classification_source": source,
        "classification_reason": reason,
        "failed_nodeids": sorted(failed_nodeids),
        "failure_excerpt": "" if status == "passed" else failure_excerpt(output),
        "diagnostics": structured_diagnostics(report),
    }


def structured_pytest_status(
    report: dict[str, Any], exit_code: int | None
) -> tuple[str, str]:
    if any(
        report.get(key)
        for key in (
            "collected_nodeids_truncated",
            "test_reports_truncated",
            "collection_reports_truncated",
        )
    ):
        return "needs_repair", "structured_report_truncated"
    collected = {str(item) for item in report.get("collected_nodeids", []) if item}
    test_reports = [
        item for item in report.get("test_reports", []) if isinstance(item, dict)
    ]
    collection_failed = any(
        item.get("outcome") == "failed"
        for item in report.get("collection_reports", [])
        if isinstance(item, dict)
    )
    internal_failed = bool(report.get("internal_errors"))
    failed = [item for item in test_reports if item.get("outcome") == "failed"]
    skipped = any(item.get("outcome") == "skipped" for item in test_reports)
    call_nodeids = {
        str(item.get("nodeid"))
        for item in test_reports
        if item.get("phase") == "call" and item.get("outcome") in {"passed", "failed"}
    }
    complete = (
        not collection_failed
        and not internal_failed
        and not skipped
        and call_nodeids == collected
    )
    if exit_code == 0 and collected and not failed and complete:
        return "passed", "completed_pass"
    if (
        exit_code == 1
        and bool(failed)
        and complete
        and all(
            item.get("phase") == "call"
            and isinstance(item.get("exception"), dict)
            and item["exception"].get("is_assertion") is True
            for item in failed
        )
    ):
        return "assertion_failed", "call_assertion_only"
    return "needs_repair", "non_assertion_or_incomplete_execution"


def structured_diagnostics(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {}
    diagnostics = {}
    for count, records in (
        ("collected_count", "collected_nodeids"),
        ("test_report_count", "test_reports"),
        ("collection_report_count", "collection_reports"),
    ):
        diagnostics[count] = int(report.get(count) or len(report.get(records, [])))
        diagnostics[f"{records}_truncated"] = bool(report.get(f"{records}_truncated"))
    return {
        **diagnostics,
        "test_failures": [
            item
            for item in report.get("test_reports", [])
            if isinstance(item, dict) and item.get("outcome") != "passed"
        ],
        "collection_failures": [
            item
            for item in report.get("collection_reports", [])
            if isinstance(item, dict) and item.get("outcome") == "failed"
        ],
        "internal_errors": report.get("internal_errors", []),
    }


def read_structured_report(report_path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def failure_excerpt(output: str, *, limit: int = 2400) -> str:
    for marker in (
        "=================================== FAILURES ===================================",
        "==================================== ERRORS ====================================",
        "Traceback",
        "short test summary info",
    ):
        if marker in output:
            return output.split(marker, 1)[1][:limit].strip()
    return output[-limit:].strip()


def run_pytest_command(
    copy_root: Path,
    python: str,
    test_file: str,
    *,
    timeout: int,
    report_path: Path,
) -> dict[str, Any]:
    report_path.unlink(missing_ok=True)
    runtime_report_dir = copy_root / ".test-augment-evidence"
    runtime_report_dir.mkdir(parents=True, exist_ok=True)
    runtime_report_path = runtime_report_dir / report_path.name
    env = build_test_env(
        copy_root, extra_env={PYTEST_REPORT_ENV: str(runtime_report_path)}
    )
    requested_cmd = [
        python,
        "-m",
        "pytest",
        "-q",
        "-c",
        str(pytest_config_for_checkout(copy_root)),
        "-p",
        "no:cacheprovider",
        "-p",
        PYTEST_REPORT_PLUGIN,
        "--rootdir",
        str(copy_root),
        test_file,
    ]
    command, sandbox = sandboxed_pytest_command(
        requested_cmd,
        copy_root=copy_root,
        test_file=test_file,
    )
    result = run_command(
        command,
        cwd=copy_root,
        timeout=timeout,
        env=env,
    )
    report = read_structured_report(runtime_report_path)
    if report is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(runtime_report_dir, ignore_errors=True)
    return {
        **result,
        **sandbox,
        "requested_cmd": requested_cmd,
        "structured_report_path": str(report_path),
        "structured_report": report,
    }
