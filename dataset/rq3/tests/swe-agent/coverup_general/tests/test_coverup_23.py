# file: sweagent/run/compare_runs.py:107-123
# asked: {"lines": [107, 108, 109, 110, 111, 113, 114, 115, 116, 117, 118, 119, 120, 121, 123], "branches": [[109, 110], [109, 111], [118, 119], [118, 120], [120, 121], [120, 123]]}
# gained: {"lines": [107, 108, 109, 110, 111, 113, 114, 115, 116, 117, 118, 119, 120, 121, 123], "branches": [[109, 110], [109, 111], [118, 119], [118, 120], [120, 121], [120, 123]]}

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def mod():
    return importlib.import_module("sweagent.run.compare_runs")


def test_run_from_cli_single_file_calls_stats_single(tmp_path, monkeypatch, mod):
    called = {}

    def fake_stats_single(p):
        # record that it was called and with which path
        called["path"] = p

    monkeypatch.setattr(mod, "stats_single", fake_stats_single)

    # create a real file
    f = tmp_path / "preds.json"
    f.write_text("{}")

    # call with single file path
    mod.run_from_cli([str(f)])

    assert "path" in called
    assert isinstance(called["path"], Path)
    # should be exactly the file passed (get_preds_path should return same for files)
    assert called["path"] == f


def test_run_from_cli_single_dir_resolves_results_json(tmp_path, monkeypatch, mod):
    called = {}

    def fake_stats_single(p):
        called["path"] = p

    monkeypatch.setattr(mod, "stats_single", fake_stats_single)

    # create a directory
    d = tmp_path / "dirA"
    d.mkdir()

    # call with directory path; get_preds_path should return dir / "results.json"
    mod.run_from_cli([str(d)])

    assert "path" in called
    expected = d / "results.json"
    assert called["path"] == expected


def test_run_from_cli_pair_calls_compare_pair_with_show_same_flag(tmp_path, monkeypatch, mod):
    called = {}

    def fake_compare_pair(p1, p2, show_same=False):
        called["p1"] = p1
        called["p2"] = p2
        called["show_same"] = show_same

    monkeypatch.setattr(mod, "compare_pair", fake_compare_pair)

    # create two files
    f1 = tmp_path / "a.json"
    f1.write_text("a")
    # create a directory for second to ensure get_preds_path maps dir -> results.json
    d2 = tmp_path / "dirB"
    d2.mkdir()

    # call with two paths and the --show-same flag
    mod.run_from_cli([str(f1), str(d2), "--show-same"] if False else ["--show-same", str(f1), str(d2)])
    # The argparse expects positional paths first unless flag before; both orders acceptable but ensure correct:
    # To be robust, call twice to cover parsing in either order? Simpler: call with flag before paths (works)

    # Since we passed flag first, assert called recorded
    assert "p1" in called and "p2" in called and "show_same" in called
    assert called["p1"] == Path(str(f1))
    assert called["p2"] == d2 / "results.json"
    assert called["show_same"] is True


def test_run_from_cli_many_calls_compare_many_and_resolves_paths(tmp_path, monkeypatch, mod):
    called = {}

    def fake_compare_many(paths):
        called["paths"] = list(paths)

    monkeypatch.setattr(mod, "compare_many", fake_compare_many)

    # create mix of files and dirs
    f1 = tmp_path / "one.json"
    f1.write_text("1")
    d2 = tmp_path / "two_dir"
    d2.mkdir()
    f3 = tmp_path / "three.json"
    f3.write_text("3")

    # call with three paths (no show-same)
    mod.run_from_cli([str(f1), str(d2), str(f3)])

    assert "paths" in called
    got = called["paths"]
    assert isinstance(got, list)
    assert len(got) == 3
    assert got[0] == f1
    assert got[1] == d2 / "results.json"
    assert got[2] == f3
