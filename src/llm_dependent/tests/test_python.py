"""Extraction and the Python augment input contract, without provider calls."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ARTIFACT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ARTIFACT / "src"))

from augment.python.input.coverage_segments import build_segment_manifest
from augment.python.input.snapshot import build_initial_metric_snapshot
from llm_dependent.python.flow import analyze_flow_project_outputs
from common.projects import load_projects

SOURCE = """from litellm import completion

def consume(value):
    return value["text"]

def unrelated():
    return "constant"

def run(messages):
    result = completion(model="fixture", messages=messages)
    if result:
        unrelated()
    return consume(result)
"""


def test_flow_and_control_modes(tmp_path):
    (tmp_path / "subject.py").write_text(SOURCE)
    outputs = analyze_flow_project_outputs(
        tmp_path, [tmp_path / "subject.py"], "fixture", ("none", "direct", "recursive")
    )
    plain = outputs["none"]
    assert plain["fixed_point"]["converged"]
    assert [item["location"]["start_line"] for item in plain["sources"]] == [10]
    lines = {item["location"]["start_line"] for item in plain["data_dependence"]}
    assert {4, 11, 13} <= lines
    assert 7 not in lines
    assert "control_dependence" not in plain
    for mode in ("direct", "recursive"):
        assert outputs[mode]["sources"] == plain["sources"]
        assert outputs[mode]["data_dependence"] == plain["data_dependence"]
        assert any(
            item["location"]["function"] == "unrelated"
            for item in outputs[mode]["control_dependence"]
        )


@pytest.mark.parametrize(
    "project",
    [name for name, row in load_projects().items() if row["language"] == "python"],
)
def test_copied_cli_output_feeds_augment(tmp_path, project):
    copied = tmp_path / "artifact"
    for name in ("cli", "common", "llm_dependent", "augment"):
        shutil.copytree(
            ARTIFACT / "src" / name,
            copied / "src" / name,
            ignore=shutil.ignore_patterns("tests", "node_modules", "__pycache__"),
        )
    (copied / "resources").mkdir()
    for name in ("run.py", "resources/projects.json"):
        shutil.copy2(ARTIFACT / name, copied / name)
    checkout = tmp_path / "checkout"
    source_root = load_projects()[project]["source_roots"][0]
    filepath = f"{source_root}/subject.py"
    source = checkout / filepath
    source.parent.mkdir(parents=True)
    source.write_text(SOURCE)
    source_base = tmp_path / "source_files.json"
    source_base.write_text(json.dumps({"files": [filepath]}))
    output = tmp_path / "regions.json"
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    result = subprocess.run(
        [
            sys.executable,
            str(copied / "run.py"),
            "llm-dependent",
            "--project",
            project,
            "--project-root",
            str(checkout),
            "--source-base",
            str(source_base),
            "--out",
            str(output),
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(output.read_text())["sources"]
    for mode in ("direct", "recursive"):
        assert output.with_name(f"regions.control_dependence_{mode}.json").exists()

    coverage = {
        "files": {
            filepath: {
                "executed_lines": [1, 3, 6, 9],
                "missing_lines": [4, 7, 10, 11, 12, 13],
                "executed_branches": [],
                "missing_branches": [[11, 12], [11, 13]],
            }
        }
    }
    (tmp_path / "coverage.json").write_text(json.dumps(coverage))
    base = tmp_path / "base.json"
    base.write_text(
        json.dumps(
            {
                "project": project,
                "project_root": "checkout",
                "ldh": {"regions_json": "regions.json"},
                "general_cov": {"coverage_json": "coverage.json"},
                "runtime": {"python": sys.executable, "coverage_source": source_root},
            }
        )
    )
    snapshot, _ = build_initial_metric_snapshot(base)
    projected = snapshot["ldh_coverage"]["files"][filepath]
    assert 7 not in projected["lines"]
    assert projected["uncovered_branches"] == ["11->12", "11->13"]
    segments = build_segment_manifest(checkout, snapshot)["segments"]
    assert segments and {item["filepath"] for item in segments} == {filepath}
