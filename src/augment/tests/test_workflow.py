import copy
import json
import re
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

from augment.python.input.snapshot import build_initial_metric_snapshot
from augment.python.run import workflow
from augment.python.run.runtime import RunOptions


def fixture(root):
    project = root / "project"
    (project / "pkg").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "pkg/__init__.py").write_text("")
    (project / "pkg/helper.py").write_text("EXPECTED = 'first-yes'\n")
    (project / "pkg/mod.py").write_text(
        "def first(value):\n"
        "    return 'first-yes' if value else 'first-no'\n\n"
        "def second(value):\n"
        "    return 'second-yes' if value else 'second-no'\n"
    )
    file = {
        "covered_lines": [],
        "uncovered_lines": [1, 2, 4, 5],
        "covered_branches": [],
        "uncovered_branches": [],
    }
    snapshot = {
        "project": "fixture",
        "ldh_coverage": {"files": {"pkg/mod.py": {**file, "lines": [1, 2, 4, 5]}}},
        "general_coverage": {
            "files": {
                "pkg/mod.py": {
                    **copy.deepcopy(file),
                    "total_lines": 4,
                    "total_branches": 0,
                }
            },
            "totals": {
                "covered_lines": 0,
                "total_lines": 4,
                "covered_branches": 0,
                "total_branches": 0,
            },
        },
    }
    return project, snapshot


def scripted_model(scenario, conversations, clock=None):
    class Model:
        def __init__(self, *args):
            self.calls = 0

        def validate(self):
            pass

        def complete_messages(self, messages, *, raw_path):
            self.calls += 1
            conversations.append(copy.deepcopy(messages))
            if clock is not None:
                clock.now += 2
            if scenario == "transport_retry" and self.calls == 1:
                raise urllib.error.URLError("temporary transport failure")
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(
                json.dumps({"response": {"usage": {"total_tokens": 2}}})
            )
            suffix = re.search(
                r'"test_name_suffix": "(_round_\d{3})"', messages[0]["content"]
            )[1]
            function = re.search(
                r'"qualname": "(first|second)"', messages[0]["content"]
            )[1]
            if (scenario == "initial_context" and self.calls == 1) or (
                scenario == "repair_context" and self.calls == 2
            ):
                return json.dumps(
                    {
                        "action": "request_context",
                        "diagnosis": "Check the return contract.",
                        "requests": [
                            {
                                "kind": "module_context",
                                "filepath": "pkg/helper.py",
                                "reason": "Expected collaborator value.",
                            }
                        ],
                    }
                )
            wrong = scenario in {"repair", "repair_context"} and self.calls == 1
            expected = "wrong" if wrong else f"{function}-yes"
            code = f"from pkg.mod import {function}\n\ndef test_ok{suffix}():\n"
            code += (
                "    assert True\n"
                if scenario == "no_gain" and self.calls == 1
                else (f"    assert {function}(True) == {expected!r}\n")
            )
            if scenario == "partial":
                code += f"\ndef test_bad{suffix}():\n    assert False\n"
            file = f"tests/test_generated{suffix}.py"
            return json.dumps(
                {
                    "action": "propose_test",
                    "test_file": file,
                    "append_code": code,
                    "expected_nodeids": [f"{file}::test_ok{suffix}"],
                    "targeted_objective_ids": [],
                    "targeted_lines": [],
                    "mocking_strategy": "none",
                    "oracle": "return value",
                }
            )

    return Model


@pytest.mark.parametrize(
    "scenario",
    [
        "direct",
        "initial_context",
        "repair",
        "repair_context",
        "partial",
        "no_gain",
        "transport_retry",
    ],
)
def test_real_pytest_workflow(tmp_path, monkeypatch, scenario):
    project, snapshot = fixture(tmp_path)
    if scenario == "no_gain":
        for dimension in ("ldh_coverage", "general_coverage"):
            snapshot[dimension]["files"]["pkg/mod.py"].update(
                covered_lines=[1, 4], uncovered_lines=[2, 5]
            )
    conversations = []
    monkeypatch.setattr(
        workflow, "ModelSession", scripted_model(scenario, conversations)
    )
    options = RunOptions(
        project="fixture",
        project_root=project,
        out_root=tmp_path / "out",
        model="fake",
        provider="openai",
        env={},
        python=sys.executable,
        coverage_source="pkg",
        rounds=2,
        run_id="smoke",
        timeout=10,
        repair_context_requests=1,
    )
    output = workflow.run_augment(snapshot=snapshot, options=options)
    rows = json.loads((output / "results.json").read_text())
    assert rows[-1]["status"] == "accepted"
    assert not (output / "workspaces").exists()
    assert list((project / "tests").iterdir()) == []
    for row in rows:
        if row["status"] == "accepted":
            assert Path(row["accepted_file_snapshot"]).is_file()
            assert row["accepted_nodeids"]
    if scenario == "partial":
        assert rows[0]["rejected_nodeids"]
        assert len(rows[0]["accepted_nodeids"]) == 1
    if scenario in {"repair", "repair_context", "no_gain"}:
        assert rows[0]["sample_id"].endswith("attempt_001")
        sample_dir = output / "rounds/round_001/sample_001"
        repair_dir = sample_dir / "repair"
        assert Path(rows[0]["prompt_path"]) == repair_dir / "feedback.md"
        assert Path(rows[0]["proposal_path"]) == repair_dir / "proposal.json"
        assert (repair_dir / "feedback.json").is_file()
        assert list(repair_dir.glob("response_*.raw.json"))
        assert not (sample_dir / "repair_001").exists()
    if scenario == "transport_retry":
        assert rows[0]["status"] == "model_failed"
        assert rows[0]["objective_id"] == rows[1]["objective_id"]
    if scenario in {"initial_context", "repair_context"}:
        assert any("EXPECTED" in str(messages) for messages in conversations[1:])
    assert json.loads((output / "coverage.json").read_text()) == snapshot
    progress = json.loads((output / "progress.json").read_text())
    assert progress["checkpoints"][-1]["round"] == len(rows)
    assert not {"accepted_count", "status_counts", "completed_rounds"} & progress.keys()
    assert not (output / "summary.json").exists()
    assert not (output / "model_usage.json").exists()
    assert list(output.rglob("*.raw.json"))
    with pytest.raises(FileExistsError):
        workflow.run_augment(snapshot=snapshot, options=options)


def test_budget_stops_before_next_round(tmp_path, monkeypatch):
    project, snapshot = fixture(tmp_path)
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(
        workflow, "time", SimpleNamespace(perf_counter=lambda: clock.now)
    )
    monkeypatch.setattr(workflow, "ModelSession", scripted_model("direct", [], clock))
    output = workflow.run_augment(
        snapshot=snapshot,
        options=RunOptions(
            project="fixture",
            project_root=project,
            out_root=tmp_path / "out",
            model="fake",
            provider="openai",
            env={},
            python=sys.executable,
            coverage_source="pkg",
            rounds=10,
            time_budget_seconds=1,
            timeout=10,
        ),
    )
    progress = json.loads((output / "progress.json").read_text())
    assert progress["stop_reason"] == "time_budget"
    assert len(json.loads((output / "results.json").read_text())) == 1


def test_input_paths_are_relative_to_packet(tmp_path):
    project, _ = fixture(tmp_path)
    (tmp_path / "regions.json").write_text(
        json.dumps(
            {
                "sources": [{"location": {"filepath": "pkg/mod.py", "start_line": 2}}],
            }
        )
    )
    (tmp_path / "coverage.json").write_text(
        json.dumps(
            {
                "files": {
                    "pkg/mod.py": {"executed_lines": [1], "missing_lines": [2]},
                }
            }
        )
    )
    packet = tmp_path / "input.json"
    packet.write_text(
        json.dumps(
            {
                "project": "fixture",
                "project_root": "unused-checkout",
                "ldh": {"regions_json": "regions.json"},
                "general_cov": {"coverage_json": "coverage.json"},
                "runtime": {"python": sys.executable, "coverage_source": "pkg"},
            }
        )
    )
    snapshot, runtime = build_initial_metric_snapshot(packet, project_root=project)
    assert Path(runtime["project_root"]) == project.resolve()
    assert snapshot["ldh_coverage"]["files"]["pkg/mod.py"]["lines"] == [2]
    interpreter = tmp_path / "venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    _, runtime = build_initial_metric_snapshot(
        packet, project_root=project, python=interpreter
    )
    assert Path(runtime["python"]) == interpreter
    data = json.loads(packet.read_text())
    data["runtime"]["python"] = "venv/bin/python"
    packet.write_text(json.dumps(data))
    _, runtime = build_initial_metric_snapshot(packet, project_root=project)
    assert Path(runtime["python"]) == interpreter


@pytest.mark.parametrize("budget", [-1, float("inf"), float("nan")])
def test_invalid_budget_is_rejected_before_execution(tmp_path, budget):
    project, snapshot = fixture(tmp_path)
    options = RunOptions(
        project="fixture",
        project_root=project,
        out_root=tmp_path / "out",
        model="fake",
        provider="openai",
        env={},
        python=sys.executable,
        coverage_source="pkg",
        time_budget_seconds=budget,
    )
    with pytest.raises(SystemExit, match="time budget"):
        workflow.run_augment(snapshot=snapshot, options=options)
    assert not options.out_root.exists()
