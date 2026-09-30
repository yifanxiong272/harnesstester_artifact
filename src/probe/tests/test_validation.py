"""Differential structured pytest evidence and subprocess completion checks."""

from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from test_compaction import formal_module
from probe.python.runtime import validate
from probe.python.run import session as sessions


def test_validation_environment_has_only_shared_runtime_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(
        os,
        "environ",
        {
            "PATH": "/fixture/bin:/usr/bin",
            "LANG": "C",
            "OPENAI_API_KEY": "fixture-secret",
            "MSWEA_SILENT_STARTUP": "inherited",
        },
    )
    env = validate.build_test_env(tmp_path)
    assert env["PATH"] == os.environ["PATH"]
    assert env["LANG"] == "C"
    assert "OPENAI_API_KEY" not in env
    assert "MSWEA_SILENT_STARTUP" not in env
    assert env["CI"] == "true"
    assert env["PYTHONHASHSEED"] == "0"
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert env["PYTHONPATH"].split(os.pathsep) == validate.validation_python_paths(
        tmp_path
    )
    for key in ("HOME", "TMPDIR", "XDG_CACHE_HOME"):
        assert Path(env[key]).parent == tmp_path
        assert Path(env[key]).is_dir()


def reports():
    base = {
        "schema": "test-augment-pytest-structured-report",
        "collected_nodeids": ["test_counter.py::test_increment"],
        "test_reports": [
            {
                "nodeid": "test_counter.py::test_increment",
                "phase": phase,
                "outcome": "passed",
            }
            for phase in ("setup", "call", "teardown")
        ],
        "collection_reports": [],
        "internal_errors": [],
    }
    values = [None, {}, base, {**base, "schema": "unknown"}]
    for key in (
        "collected_nodeids_truncated",
        "test_reports_truncated",
        "collection_reports_truncated",
    ):
        values.append({**base, key: True})
    for phase in ("setup", "call", "teardown"):
        for assertion in (True, False, None):
            item = deepcopy(base)
            item["test_reports"].append(
                {
                    "nodeid": "test_counter.py::test_increment",
                    "phase": phase,
                    "outcome": "failed",
                    "exception": {"is_assertion": assertion},
                }
            )
            values.append(item)
    values.extend(
        [
            {**base, "internal_errors": ["fixture"]},
            {**base, "collected_nodeids": []},
            {**base, "collected_nodeids": ["test_counter.py::test_other"]},
            {**base, "test_reports": []},
            {**base, "collection_reports": [{"outcome": "failed"}]},
            {**base, "test_reports": [*base["test_reports"], {"outcome": "skipped"}]},
        ]
    )
    return values


@pytest.mark.parametrize("report", reports())
def test_pytest_classification_matches_formal(report):
    formal = formal_module("validate", "runtime")
    for exit_code in (None, 0, 1, 2, 5):
        for timed_out in (False, True):
            for output in (
                "",
                "Traceback\nValueError: fixture",
                "FAILED test_counter.py::test_increment - fixture",
            ):
                assert validate.pytest_evidence(
                    output, exit_code, timed_out, report=report
                ) == formal.pytest_evidence(output, exit_code, timed_out, report=report)


def test_validation_summary_retains_canonical_evidence(tmp_path, monkeypatch):
    formal = formal_module("validate", "runtime")
    checkout = tmp_path / "source"
    checkout.mkdir()
    session = sessions.ValidationSession(
        {"revisions": {"buggy": "before"}},
        {"buggy": checkout},
        {"buggy": "fixture-python"},
        30,
    )
    proposal = SimpleNamespace(
        test_file="tests/test_counter.py", append_code="assert True\n"
    )
    for index, report in enumerate(reports()):
        output = "prefix " * 1200 + "\nFAILED test_counter.py::test_increment - fixture"
        raw = {
            "exit_code": index % 3,
            "timed_out": index % 5 == 0,
            "output_tail": output,
            "structured_report": report,
        }
        monkeypatch.setattr(sessions, "run_pytest_command", lambda *args, **kwargs: raw)
        sample_dir = tmp_path / str(index)
        result = session.run("buggy", proposal, tmp_path / "proposal.json", sample_dir)
        evidence = formal.pytest_evidence(
            output, raw["exit_code"], raw["timed_out"], report=report
        )
        assert result["summary"] == {
            "revision": "before",
            "passed": evidence["passed"],
            "status": evidence["status"],
            "classification_source": evidence["classification_source"],
            "classification_reason": evidence["classification_reason"],
            "diagnostics": evidence["diagnostics"],
            "phase": "pytest",
            "exit_code": raw["exit_code"],
            "timed_out": raw["timed_out"],
            "failed_nodeids": evidence["failed_nodeids"],
            "failure_excerpt": evidence["failure_excerpt"],
            "output_tail": output[-8000:],
            "setup_policy": "prepared",
        }
        assert result["result"]["evidence"] == evidence
        assert result["materialized"]["cleanup"]["removed"]


@pytest.mark.parametrize(
    "nodeids",
    [
        [],
        [None, "", 0, False],
        ["test_counter.py::b", "test_counter.py::a", "test_counter.py::b"],
        ["test_counter.py::a", 3, True, ["nested"]],
    ],
)
def test_pytest_nodeids_preserve_structured_precedence_and_deduplication(nodeids):
    formal = formal_module("validate", "runtime")
    report = {
        "schema": "test-augment-pytest-structured-report",
        "collected_nodeids": nodeids,
        "test_reports": [
            {
                "nodeid": nodeid,
                "phase": "call",
                "outcome": "failed",
                "exception": {"is_assertion": True},
            }
            for nodeid in nodeids
        ]
        + [None, [], "invalid record"],
    }
    output = "FAILED fallback.py::b\nFAILED fallback.py::a\nFAILED fallback.py::b"
    actual = validate.pytest_evidence(output, 1, False, report=report)
    assert actual == formal.pytest_evidence(output, 1, False, report=report)
    assert actual["failed_nodeids"] == (
        sorted({str(nodeid) for nodeid in nodeids if nodeid})
        or ["fallback.py::a", "fallback.py::b"]
    )


@pytest.mark.parametrize(
    "scenario",
    [
        "passed",
        "failed",
        "timeout",
        "spawn_error",
        "budget",
        "timeout_budget",
    ],
)
def test_process_results_and_deadline_order_match_formal(
    tmp_path, monkeypatch, scenario
):
    observed = []
    for module in (validate, formal_module("validate", "runtime")):
        events = []
        limits = []

        def limit(seconds=float("inf")):
            limits.append(seconds)
            if len(limits) == 2 and scenario in {"budget", "timeout_budget"}:
                raise module.CaseTimeBudgetExceeded("fixture deadline")
            return seconds

        class Process:
            returncode = 1 if scenario == "failed" else 0
            stdout = None

            def __init__(self, cmd, **kwargs):
                events.append(("spawn", cmd, kwargs))
                if scenario == "spawn_error":
                    raise FileNotFoundError("fixture executable")
                self.calls = 0

            def communicate(self, timeout=None):
                self.calls += 1
                events.append(("communicate", timeout))
                if scenario in {"timeout", "timeout_budget"} and self.calls == 1:
                    raise subprocess.TimeoutExpired(
                        ["fixture"], timeout, output="partial"
                    )
                return "fixture output" * 1000, None

        def cleanup(process, force=False):
            events.append(("cleanup", process is not None, force))
            return {"attempted": True, "signal": "SIGKILL" if force else "SIGTERM"}

        with monkeypatch.context() as patch:
            patch.setattr(module.subprocess, "Popen", Process)
            patch.setattr(module, "terminate_process_group", cleanup)
            patch.setattr(module, "limit_timeout", limit)
            try:
                result = module.run_command(
                    ["fixture"], cwd=tmp_path, timeout=12, env={}
                )
            except module.CaseTimeBudgetExceeded as exc:
                result = {"budget_error": str(exc)}
            observed.append((result, events, limits))
    formal_result, formal_events, formal_limits = observed[1]
    if scenario in {"timeout", "timeout_budget"}:
        # The artifact now bounds the post-kill drain; other lifecycle order stays.
        formal_events[-1] = ("communicate", 1)
    assert observed[0] == (formal_result, formal_events, formal_limits)
    if scenario in {"budget", "timeout_budget"}:
        assert "budget_error" in observed[0][0]
