"""Latest-revision eligibility and candidate selection against the formal runner."""

from __future__ import annotations

import copy
import os
from dataclasses import replace
from types import SimpleNamespace

import pytest

from test_compaction import (
    formal_module,
    formal_prompts_without_test_command,
    formal_run_options,
)
from test_python_probe import FixedModel, fixture, formal_evidence, options
from probe.python.run.discovery import is_discovery_failure
from probe.python.run.workflow import run_target_sample
from probe.python.runtime.validate import pytest_evidence

MODE = "single_revision_discovery"


def exception_summary(**changes):
    return {
        "status": "needs_repair",
        "passed": False,
        "timed_out": False,
        "classification_source": "structured_reporter",
        "classification_reason": "non_assertion_or_incomplete_execution",
        "failed_nodeids": ["tests/test_counter.py::test_advance"],
        "failure_excerpt": "ValueError: cannot advance",
        "diagnostics": {"test_failures": [{"outcome": "failed", "phase": "call"}]},
        **changes,
    }


def formal_discovery_with_current_diagnostics(monkeypatch):
    """Adapt the formal consumer's diagnostic key for the approved artifact fix."""
    formal = formal_module("candidate")
    original = formal.is_discovery_failure

    def aligned(summary):
        diagnostics = summary.get("diagnostics") or {}
        return original({
            **summary,
            "diagnostics": {**diagnostics, "test_reports": diagnostics.get("test_failures", [])},
        })

    monkeypatch.setattr(formal, "is_discovery_failure", aligned)
    return formal


@pytest.mark.parametrize(
    "changes,eligible",
    [
        ({}, True),
        ({"status": "assertion_failed"}, True),
        ({"status": "passed", "passed": True}, False),
        ({"timed_out": True}, False),
        ({"classification_source": "text"}, False),
        ({"classification_reason": "collection_error"}, False),
        ({"failed_nodeids": []}, False),
        ({"diagnostics": {}}, False),
        (
            {
                "diagnostics": {
                    "test_failures": [{"outcome": "failed", "phase": "setup"}]
                }
            },
            False,
        ),
        (
            {
                "diagnostics": {
                    "test_failures": [
                        {"outcome": "failed", "phase": "call"},
                        {"outcome": "failed", "phase": "teardown"},
                    ]
                }
            },
            False,
        ),
    ],
)
def test_discovery_eligibility(monkeypatch, changes, eligible):
    summary = exception_summary(**changes)
    assert is_discovery_failure(summary) is eligible
    if os.environ.get("PROBE_FORMAL_ROOT"):
        formal = formal_discovery_with_current_diagnostics(monkeypatch)
        assert is_discovery_failure(summary) == formal.is_discovery_failure(summary)


@pytest.mark.parametrize("phase", ["setup", "call", "teardown"])
@pytest.mark.parametrize("condition", ["complete", "timeout", "truncated", "missing_report"])
def test_discovery_uses_produced_pytest_diagnostics(phase, condition):
    nodeid = "tests/test_counter.py::test_advance"
    report = {
        "schema": "test-augment-pytest-structured-report",
        "collected_nodeids": [nodeid],
        "collection_reports": [],
        "internal_errors": [],
        "test_reports": [
            {
                "nodeid": nodeid,
                "phase": current,
                "outcome": "failed" if current == phase else "passed",
                "exception": {"is_assertion": False} if current == phase else None,
            }
            for current in ("setup", "call", "teardown")
            if not (phase == "setup" and current == "call")
        ],
        "test_reports_truncated": condition == "truncated",
    }
    summary = pytest_evidence(
        "ValueError: cannot advance", 1, condition == "timeout",
        report=None if condition == "missing_report" else report,
    )
    assert "test_reports" not in summary["diagnostics"]
    assert is_discovery_failure(summary) == (phase == "call" and condition == "complete")


@pytest.mark.parametrize(
    "strategy", ["target_probe_ldh", "target_probe_contract_agnostic"]
)
@pytest.mark.parametrize(
    "scenario,status",
    [
        ("passed", "latest_passed"),
        ("exception", "stable_failure_candidate"),
        ("setup", "latest_needs_repair"),
        ("fingerprint_drift", "unstable_failure"),
        ("repair_passed", "latest_needs_repair"),
        ("minimized_drift", "stable_failure_candidate"),
    ],
)
def test_discovery_candidates(tmp_path, monkeypatch, strategy, scenario, status):
    roots, _, packet, plan, asset = fixture(tmp_path)
    packet.update(evaluation_mode=MODE, strategy=strategy)
    replies = [plan, {"assets": [asset]}]
    if scenario in {"exception", "setup"}:
        replies.append({"action": "retain_original"})
    elif scenario == "repair_passed":
        replies.append(
            {"action": "repair", "assets": [{**asset, "asset_id": "repaired"}]}
        )
    elif scenario == "minimized_drift":
        replies.append({"assets": [{**asset, "asset_id": "minimized"}]})
    configured = replace(
        options(),
        evaluation_mode=MODE,
        strategy=strategy,
        minimize_buggy_failures_per_sample=int(scenario == "minimized_drift"),
    )

    class Validation:
        def __init__(self):
            self.calls = []

        def run(self, revision_kind, proposal, proposal_path, sample_dir):
            self.calls.append((revision_kind, proposal.to_dict(), str(sample_dir)))
            assert revision_kind == "latest"
            summary = exception_summary(status="assertion_failed")
            if scenario in {"exception", "setup", "repair_passed"}:
                summary = exception_summary()
            if scenario == "setup":
                summary["diagnostics"]["test_failures"][0]["phase"] = "setup"
            if scenario == "passed" or proposal.asset_id == "repaired":
                summary.update(status="passed", passed=True, failed_nodeids=[])
            if (scenario == "fingerprint_drift" and len(self.calls) == 2) or (
                scenario == "minimized_drift"
                and "minimized-confirmation" in sample_dir.name
            ):
                summary["failure_excerpt"] = "different failure"
            return {
                "summary": summary,
                "result": {"evidence": summary},
                "materialized": {},
            }

    observed = []
    runners = [run_target_sample]
    if os.environ.get("PROBE_FORMAL_ROOT"):
        formal_prompts_without_test_command(monkeypatch)
        formal_discovery_with_current_diagnostics(monkeypatch)
        runners.append(formal_module("workflow").run_target_sample)
    for index, run in enumerate(runners):
        model, validation = FixedModel(copy.deepcopy(replies)), Validation()
        runtime = SimpleNamespace(
            manifest={
                "evaluation_mode": MODE,
                "source_roots": ["arithmetic.py"],
                "latest_checkout": {"path": str(roots["buggy"])},
            },
            options=formal_run_options(configured) if index else configured,
            model=model,
            validation=validation,
        )
        row = run(
            runtime=runtime,
            packet=copy.deepcopy(packet),
            sample_id="direct-001",
            sample_dir=tmp_path / "sample",
            prior_attempts=[],
            prompt_style="direct",
            harness_repair_budget=1,
        )
        assert not model.responses
        row = formal_evidence(row) if index else row
        result = row["assets"][0]
        assert result["status"] == status
        assert "fixed" not in result and "buggy" not in result
        if scenario == "minimized_drift":
            assert result["asset_id"] == asset["asset_id"]
            assert result["confirmation"]["stable"]
            assert len(validation.calls) == 6
        if scenario == "fingerprint_drift":
            assert len(validation.calls) == 3
            assert [run["passed"] for run in result["confirmation"]["runs"]] == [
                False,
                True,
            ]
        observed.append((row, model.prompts, validation.calls))
    if len(observed) == 2:
        assert observed[0] == observed[1]
