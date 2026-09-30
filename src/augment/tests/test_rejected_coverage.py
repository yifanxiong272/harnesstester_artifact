"""Rejected candidates must not contribute to the accepted coverage state."""

from copy import deepcopy
import json
import sys

import pytest

from augment.python.run import workflow
from augment.python.run.runtime import RunOptions
from test_candidate_reference import run_candidate
from augment.python.run import candidate
from test_workflow import fixture, scripted_model


@pytest.mark.parametrize("policy", ["passing_subset", "candidate_atomic"])
@pytest.mark.parametrize("scenario", ["success", "empty", "wrong_round", "collect_failed"])
def test_candidate_only_exposes_accepted_coverage(tmp_path, policy, scenario):
    row, _, evidence = run_candidate(candidate, tmp_path, policy, scenario)
    if scenario == "success":
        assert row["status"] == "accepted"
        assert row["accepted_coverage_path"]
        assert "measured_coverage_path" not in row
    else:
        assert row["status"] == "round_nodeid_missing"
        assert row["accepted_coverage_path"] == ""
        if policy == "candidate_atomic":
            assert row["measured_coverage_path"].endswith("accepted_coverage.json")
            assert "accepted_coverage.json" in evidence
            update = json.loads(evidence["coverage_update.json"])
            assert update["accepted_coverage_path"] == ""
            assert update["measured_coverage_path"] == row["measured_coverage_path"]


def options(root, project):
    return RunOptions(
        project="fixture", project_root=project, out_root=root / "out",
        model="scripted", provider="openai", env={}, python=sys.executable,
        coverage_source="pkg", rounds=1, timeout=10,
        acceptance_policy="candidate_atomic",
    )


@pytest.mark.parametrize("valid_name", [False, True])
def test_atomic_workflow_keeps_only_accepted_measurements(tmp_path, monkeypatch, valid_name):
    project, snapshot = fixture(tmp_path)
    before = deepcopy(snapshot)

    class Model(scripted_model("direct", [])):
        def complete_messages(self, messages, *, raw_path):
            response = super().complete_messages(messages, raw_path=raw_path)
            return response if valid_name else response.replace("test_ok_round_001", "test_wrong")

    monkeypatch.setattr(workflow, "ModelSession", Model)
    out = workflow.run_augment(snapshot=snapshot, options=options(tmp_path, project))
    row = json.loads((out / "results.json").read_text())[0]
    saved = json.loads((out / "coverage.json").read_text())
    accepted = list((out / "accepted").rglob("*.py"))
    if valid_name:
        assert row["status"] == "accepted" and len(accepted) == 1
        assert saved["general_coverage"]["totals"]["covered_lines"] > 0
    else:
        assert row["status"] == "round_nodeid_missing"
        assert not accepted and not row["accepted_nodeids"]
        assert row["accepted_coverage_path"] == ""
        assert saved == before == snapshot


@pytest.mark.parametrize("status", ["accepted", "round_nodeid_missing", "validation_failed"])
def test_workflow_checks_status_even_when_a_coverage_path_is_present(tmp_path, monkeypatch, status):
    project, snapshot = fixture(tmp_path)
    before = deepcopy(snapshot)
    measured = tmp_path / "measured.json"
    measured.write_text(json.dumps({"files": {"pkg/mod.py": {"executed_lines": [1]}}}))
    monkeypatch.setattr(workflow, "ModelSession", scripted_model("direct", []))
    monkeypatch.setattr(workflow, "execute_sample", lambda *args: {
        "status": status, "accepted_nodeids": [], "accepted_coverage_path": str(measured),
    })
    workflow.run_augment(snapshot=snapshot, options=options(tmp_path, project))
    assert (snapshot != before) == (status == "accepted")
