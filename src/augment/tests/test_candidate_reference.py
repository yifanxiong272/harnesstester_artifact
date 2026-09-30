"""Compare validation policy decisions and saved evidence with the formal runner."""

import importlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from augment.python.run import candidate


class ScriptedValidation:
    def __init__(self, scenario, directory):
        self.scenario = scenario
        self.directory = directory
        self.calls = []

    def record(self, action, **details):
        self.calls.append(
            (action, details, (self.directory / "validation.json").exists())
        )
        if self.scenario == f"raise_{action}":
            raise RuntimeError(f"{action} interrupted")

    def collect(self, root, test_file, *, keyword):
        self.record("collect", test_file=test_file, keyword=keyword)
        nodeids = [f"{test_file}::test_{name}{keyword}" for name in ("a", "b")]
        nodeids.append(f"{test_file}::test_unrelated")
        if self.scenario in {"empty", "collect_failed"}:
            nodeids = []
        if self.scenario == "wrong_round":
            nodeids = [f"{test_file}::test_a_round_002"]
        return nodeids, {
            "exit_code": 1 if self.scenario == "collect_failed" else 0,
            "output_tail": "collection output",
        }

    def filter_passing(self, root, nodeids):
        self.record("filter", nodeids=nodeids)
        accepted = (
            []
            if self.scenario == "all_failed"
            else nodeids[:1]
            if self.scenario == "partial"
            else nodeids
        )
        return {
            "generated_nodeids": nodeids,
            "accepted_nodeids": accepted,
            "rejected_nodeids": [
                {"nodeid": nodeid, "exit_code": 1}
                for nodeid in nodeids
                if nodeid not in accepted
            ],
            "execution_count": len(nodeids),
        }

    def coverage(self, root, selectors, out_path, *, fail_fast=False):
        self.record("coverage", selectors=selectors, fail_fast=fail_fast)
        if self.scenario != "missing_coverage":
            out_path.write_text(
                json.dumps(
                    {
                        "files": {
                            "src/target.py": {
                                "executed_lines": [1, 2],
                                "executed_branches": [[1, 2]],
                            }
                        }
                    }
                )
            )
        result = {
            "coverage_run": {
                "exit_code": 1 if self.scenario == "coverage_failed" else 0,
                "output_tail": "test execution output",
            },
            "coverage_json": {
                "exit_code": 1 if self.scenario == "json_failed" else 0,
                "output_tail": "coverage export output",
            },
        }
        if self.scenario == "missing_run":
            result["coverage_run"] = None
        if self.scenario == "missing_exit":
            result["coverage_run"].pop("exit_code")
        return result


def run_candidate(module, root, policy, scenario):
    subject = root / "subject"
    (subject / "src").mkdir(parents=True)
    (subject / "src/target.py").write_text("flag = True\nvalue = 1\n")
    directory = root / "run/attempt"
    directory.mkdir(parents=True)
    validation = ScriptedValidation(scenario, directory)
    context = SimpleNamespace(
        current_root=subject,
        run_dir=root / "run",
        validation=validation,
        options=SimpleNamespace(project_root=subject, acceptance_policy=policy),
    )
    uncovered = {"uncovered_lines": [1, 2], "uncovered_branches": ["1->2"]}
    sample = SimpleNamespace(
        round_index=1,
        objective={
            "filepath": "src/target.py",
            "unit": {"unit_id": "target:module"},
            "general_coverage": uncovered,
        },
        snapshot={"general_coverage": {"files": {"src/target.py": uncovered}}},
    )
    test_file = "tests/test_generated_round_001.py"
    proposal = {
        "test_file": test_file,
        "append_code": "def test_a_round_001():\n    assert True\n",
        "expected_nodeids": [
            f"{test_file}::test_a_round_001",
            f"{test_file}::test_missing_round_001",
        ],
    }
    if scenario == "invalid_proposal":
        proposal["test_file"] = "tests/test_wrong.py"
    attempt = module.CandidateAttempt(directory, "sample_001", {"iteration": 1})
    try:
        result = module.validate_candidate(context, sample, proposal, attempt)
    except RuntimeError as exc:
        result = {"exception": type(exc).__name__, "message": str(exc)}
    assert not (root / "run/workspaces/staging/sample_001").exists()
    evidence = {
        path.name: path.read_text().replace(str(root), "<run>")
        for path in directory.iterdir()
        if path.is_file()
    }
    result = json.loads(json.dumps(result).replace(str(root), "<run>"))
    return result, validation.calls, evidence


@pytest.mark.parametrize("policy", ["passing_subset", "candidate_atomic"])
@pytest.mark.parametrize(
    "scenario",
    [
        "success",
        "partial",
        "all_failed",
        "empty",
        "wrong_round",
        "collect_failed",
        "coverage_failed",
        "json_failed",
        "missing_coverage",
        "missing_run",
        "missing_exit",
        "raise_collect",
        "raise_filter",
        "raise_coverage",
        "invalid_proposal",
    ],
)
def test_candidate_matches_formal(tmp_path, policy, scenario):
    root = os.environ.get("AUGMENT_FORMAL_ROOT") or os.environ.get("PROBE_FORMAL_ROOT")
    if not root:
        pytest.skip("set AUGMENT_FORMAL_ROOT for reference checks")
    import common

    directory = str(Path(root) / "src/common")
    if directory not in common.__path__:
        common.__path__.append(directory)
    formal = importlib.import_module("common.test_augmentF.python.run.candidate")
    expected = run_candidate(formal, tmp_path / "formal", policy, scenario)
    actual = run_candidate(candidate, tmp_path / "artifact", policy, scenario)
    if policy == "candidate_atomic" and scenario in {"empty", "wrong_round", "collect_failed"}:
        row, _, evidence = expected
        assert row["status"] == "round_nodeid_missing"
        assert row["accepted_nodeids"] == []
        measured = row["accepted_coverage_path"]
        assert measured
        row.update(accepted_coverage_path="", measured_coverage_path=measured)
        update = json.loads(evidence["coverage_update.json"])
        assert update["accepted_coverage_path"] == measured
        update.update(accepted_coverage_path="", measured_coverage_path=measured)
        assert json.loads(actual[2]["coverage_update.json"]) == update
        evidence["coverage_update.json"] = actual[2]["coverage_update.json"]
    assert actual == expected
