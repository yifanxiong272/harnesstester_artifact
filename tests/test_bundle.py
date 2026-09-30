"""Check the runnable input bundle without installing subjects or calling models."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from augment.python.input.snapshot import build_initial_metric_snapshot

PROJECTS = json.loads((ROOT / "resources/projects.json").read_text())


@pytest.mark.parametrize("project", PROJECTS)
def test_subject_and_input_paths(project):
    subject = ROOT / "resources/subjects" / project
    assert subject.is_dir()
    assert list(subject.glob("LICENSE*")), project
    assert not (subject / ".git").exists()
    assert not (subject / ".env").exists()
    directory = ROOT / "resources/inputs" / project
    base = json.loads((directory / "base_input.json").read_text())
    assert base["project"] == project
    assert (directory / base["project_root"]).resolve() == subject.resolve()
    inputs = [base["ldh"]["regions_json"], base["general_cov"]["coverage_json"]]
    for value in inputs:
        assert not Path(value).is_absolute()
        assert (directory / value).is_file()
    assert (directory / "regions.json").is_file()
    expected = {
        "base_input.json",
        "regions.json",
        "coverage.json",
        "source_files.json",
    }
    if PROJECTS[project]["language"] == "python":
        expected.add("requirements.txt")
        assert (directory / base["runtime"]["python"]).resolve() == (
            ROOT / ".venvs" / project / "bin/python"
        ).resolve()
    assert {entry.name for entry in directory.iterdir()} == expected
    scope = json.loads((directory / "source_files.json").read_text())
    assert set(scope) == {"files"}
    files = scope["files"]
    assert isinstance(files, list) and files
    assert len(files) == len(set(files))
    for file in files:
        assert not Path(file).is_absolute() and ".." not in Path(file).parts
        assert (subject / file).is_file(), file


@pytest.mark.parametrize(
    "project", [p for p, c in PROJECTS.items() if c["language"] == "python"]
)
def test_python_inputs_load_and_resolve_to_bundled_source(project):
    directory = ROOT / "resources/inputs" / project
    snapshot, runtime = build_initial_metric_snapshot(directory / "base_input.json")
    assert snapshot["ldh_coverage"]["files"]
    for filepath in snapshot["ldh_coverage"]["files"]:
        assert (Path(runtime["project_root"]) / filepath).is_file(), filepath
    requirements = (directory / "requirements.txt").read_text().splitlines()
    assert any(line.startswith("pytest==") for line in requirements)
    assert any(line.startswith("coverage==") for line in requirements)


@pytest.mark.parametrize("project", PROJECTS)
def test_inputs_have_no_local_machine_paths(project):
    for path in (ROOT / "resources/inputs" / project).iterdir():
        text = path.read_text()
        assert "/Users/" not in text
        assert "/home/" not in text
        assert "file://" not in text
