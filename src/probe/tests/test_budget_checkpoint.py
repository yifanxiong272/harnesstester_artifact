"""Confirmed candidates survive budget exhaustion during optional work."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from test_python_probe import fixture, options
from probe.python.run import case as case_runner, deadline, session
from probe.python.run.progress import confirmed_candidate_count


@pytest.mark.parametrize("mode", ["paired_reveal", "single_revision_discovery"])
@pytest.mark.parametrize("strategy", ["target_probe_ldh", "target_probe_contract_agnostic"])
@pytest.mark.parametrize(
    "stage",
    ["minimization", "minimized_confirmation", "initial_confirmation", "sibling", "complete"],
)
def test_case_recovers_confirmed_candidates(tmp_path, monkeypatch, mode, strategy, stage):
    roots, case, _, plan, asset = fixture(tmp_path)
    latest = mode == "single_revision_discovery"
    assets = [asset]
    if stage == "sibling":
        assets.append({**asset, "asset_id": "sibling", "input_construction": "call with one"})
    minimized = {**asset, "asset_id": "minimized"}
    responses = [plan, {"assets": assets}, {"assets": [minimized]}]
    calls = []

    def expire():
        deadline._deadline.set(0.0)
        deadline.limit_timeout()

    def completion(**kwargs):
        calls.append(kwargs["prompt"])
        if stage == "minimization" and len(calls) == 3:
            # The response completes as the shared deadline expires.
            deadline._deadline.set(0.0)
        return {"choices": [{"message": {"content": json.dumps(responses.pop(0))}}]}

    class Validation:
        def run(self, revision_kind, proposal, proposal_path, sample_dir):
            if stage == "sibling" and proposal.asset_id == "sibling":
                expire()
            if stage == "initial_confirmation" and "base-confirmation" in sample_dir.name:
                expire()
            if stage == "minimized_confirmation" and "minimized-confirmation" in sample_dir.name:
                expire()
            passed = revision_kind == "fixed"
            summary = {
                "status": "passed" if passed else "assertion_failed",
                "passed": passed,
                "timed_out": False,
                "classification_source": "structured_reporter",
                "classification_reason": "assertion_failure",
                "failed_nodeids": [] if passed else ["test_advance"],
                "failure_excerpt": "AssertionError: 1 != 2",
                "diagnostics": {"test_failures": [{"phase": "call", "outcome": "failed"}]},
            }
            return {"summary": summary, "result": {"evidence": summary}, "materialized": {}}

    monkeypatch.setattr(session, "chat_completion", completion)
    monkeypatch.setattr(case_runner, "preflight_target_run", lambda **_: {"passed": True})
    monkeypatch.setattr(
        case_runner, "run_revision_validation_preflight",
        lambda **_: {"passed": True, "target_import": {"attempted": False}},
    )
    if latest:
        case["target_units"] = case["patch_targets"]["target_units"]
        case["revisions"] = {"latest": "before"}
    configured = replace(
        options(), strategy=strategy, evaluation_mode=mode,
        minimize_buggy_failures_per_sample=int(stage != "sibling"),
    )
    run_dir = case_runner.run_prepared_case(
        case=case,
        **({"latest_root": roots["buggy"]} if latest else {
            "buggy_root": roots["buggy"], "fixed_root": roots["fixed"],
        }),
        config={"project": "fixture", "source_roots": ["arithmetic.py"]},
        options=configured,
        run_dir=tmp_path / "run",
        interpreters={},
        model=session.ModelSession("fixture", "fixture", {}, 30, 0),
        validation=Validation(),
    )
    progress = json.loads((run_dir / "progress.json").read_text())
    rows = [json.loads(Path(item["result_path"]).read_text()) for item in progress["samples"]]
    assert confirmed_candidate_count(rows, mode) == int(stage != "initial_confirmation")
    assert ("error" in progress) == (stage != "complete")
    if stage != "complete":
        assert progress["error"]["type"] == "CaseTimeBudgetExceeded"
    if rows:
        row = rows[0]
        assert row["strategy"] == strategy
        assert row["lane"] == "direct_probe"
        assert row["evaluation_mode"] == mode
        assert len(row["assets"]) == 1
        result = row["assets"][0]
        assert result["asset_id"] == ("minimized" if stage == "complete" else asset["asset_id"])
        proposal = json.loads(Path(result["proposal_path"]).read_text())
        assert proposal["append_code"] == asset["append_code"]
        confirmation = result["confirmation"] if latest else result["fixed_variants"][-1]["confirmation"]
        assert confirmation["stable"]
        assert len(confirmation["runs"]) == configured.reveal_confirmation_runs
    assert deadline.limit_timeout(1) == 1
