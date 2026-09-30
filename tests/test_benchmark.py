"""Check the bundled benchmark's cases and dependency archives."""

import json
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TARGET_FIELDS = {"filepath", "qualname", "kind", "start_line", "end_line"}
VALIDATION_FIELDS = {"test_command", "generated_test_roots", "python_import_roots"}


def read(path):
    return json.loads(path.read_text())


def test_bundled_cases_are_complete_and_portable():
    expected = {
        "openhands": 42,
        "aider": 19,
        "swe-agent": 7,
        "pr-agent": 11,
        "gpt-researcher": 4,
        "browser-use": 41,
        "rd-agent": 16,
        "openclaw": 88,
        "roo-code": 16,
        "kimi-code": 6,
    }
    benchmark = ROOT / "resources/benchmark"
    archives, targets = set(), 0
    for project, count in expected.items():
        paths = list((benchmark / "cases" / project).glob("*.json"))
        assert len(paths) == count
        for path in paths:
            case = read(path)
            assert case["project"] == project and case["case_id"] == path.stem
            assert set(case) <= {
                "case_id",
                "project",
                "repository",
                "revisions",
                "patch_targets",
                "validation",
                "dependencies",
            }
            assert set(case["revisions"]) == {"buggy", "fixed"}
            assert all(re.fullmatch(r"[0-9a-f]{40}", revision) for revision in case["revisions"].values())
            assert case["repository"].startswith("https://github.com/")
            assert set(case["patch_targets"]) == {"target_units"}
            assert case["patch_targets"]["target_units"]
            for unit in case["patch_targets"]["target_units"]:
                targets += 1
                assert set(unit) == set(TARGET_FIELDS)
                assert 1 <= unit["start_line"] <= unit["end_line"]
                filepath = Path(unit["filepath"])
                assert not filepath.is_absolute() and ".." not in filepath.parts
            assert set(case["dependencies"]) == {"buggy", "fixed"}
            for kind in ("buggy", "fixed"):
                archive = (path.parent / case["dependencies"][kind]).resolve()
                assert archive.is_relative_to(benchmark.resolve()) and archive.is_file()
                archives.add(archive)
            assert (
                "/Users/" not in path.read_text() and "/home/" not in path.read_text()
            )
    assert targets == 443
    assert archives == {
        path.resolve() for path in (benchmark / "dependencies").glob("*/*.zip")
    }
    for path in archives:
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
            assert archive.namelist()
            for name in archive.namelist():
                assert not Path(name).is_absolute() and ".." not in Path(name).parts


def test_case_validation_inputs():
    paths = list((ROOT / "resources/benchmark/cases").glob("*/*.json"))
    assert len({p.stem for p in paths}) == len(paths)
    for path in paths:
        validation = read(path)["validation"]
        assert set(validation) <= VALIDATION_FIELDS
        assert validation["test_command"]
        assert all(isinstance(part, str) and part for part in validation["test_command"])
        for key in ("generated_test_roots", "python_import_roots"):
            for root in validation.get(key, []):
                assert not Path(root).is_absolute() and ".." not in Path(root).parts


def test_supplemental_python_locks_target_ubuntu():
    locks = []
    for path in (ROOT / "resources/benchmark/dependencies").glob("*/*.zip"):
        with zipfile.ZipFile(path) as archive:
            if "resolved/requirements.lock" in archive.namelist():
                locks.append(archive.read("resolved/requirements.lock").decode())
    assert locks
    for lock in locks:
        assert "--python-platform x86_64-unknown-linux-gnu" in lock.splitlines()[1]
        assert not re.search(r"^pyobjc[^\s=]*==", lock, re.MULTILINE)
