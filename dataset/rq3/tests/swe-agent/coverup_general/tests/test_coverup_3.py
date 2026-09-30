# file: sweagent/run/compare_runs.py:26-66
# asked: {"lines": [26, 27, 28, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 61, 62, 63, 64, 65, 66], "branches": [[29, 30], [29, 32], [36, 37], [36, 38], [38, 39], [38, 40], [43, 44], [43, 49], [51, 52], [51, 56], [63, 64], [63, 66]]}
# gained: {"lines": [26, 27, 28, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 61, 62, 63, 64, 65, 66], "branches": [[29, 30], [29, 32], [36, 37], [36, 38], [38, 39], [38, 40], [43, 44], [43, 49], [51, 52], [51, 56], [63, 64], [63, 66]]}

import pytest
from pathlib import Path

import sweagent.run.compare_runs as cr


def test_compare_many_varied_emojis(monkeypatch, tmp_path, capsys):
    # Prepare two fake paths
    p1 = tmp_path / "run1" / "submission.txt"
    p2 = tmp_path / "run2" / "submission.txt"

    # Define submitted and resolved sets for each path to exercise all emoji branches:
    # - id 'a' is evaluated in both runs, resolved only in p1 -> ✅ for p1, ❌ for p2
    # - id 'b' is evaluated in p1 only, not in p2 -> ❌ for p1, ❓ for p2
    def fake_get_submitted(path: Path):
        if path == p1:
            return ["a", "b"]
        if path == p2:
            return ["a"]
        return []

    def fake_get_resolved(path: Path):
        if path == p1:
            return ["a"]
        if path == p2:
            return []
        return []

    monkeypatch.setattr(cr, "get_submitted", fake_get_submitted, raising=False)
    monkeypatch.setattr(cr, "get_resolved", fake_get_resolved, raising=False)

    # Call the function under test
    cr.compare_many([p1, p2])

    out = capsys.readouterr().out

    # Check that headers and run names appear
    assert "ID" in out
    assert "run1" in out
    assert "run2" in out

    # Check emoji counts: one ✅ (a in p1), two ❌ (a in p2 and b in p1), one ❓ (b in p2)
    assert out.count("✅") == 1
    assert out.count("❌") == 2
    assert out.count("❓") == 1

    # Check success rate formatting for individual ids: 'a' -> 0.50, 'b' -> 0.00
    assert "0.50" in out
    assert "0.00" in out

    # Final table should include success counts per run
    assert "Successes" in out
    # p1 has 1 success (a), p2 has 0
    assert "1" in out  # at least one '1' appears (success count for run1)
    assert "0.00" in out  # run2 success rate printed


def test_compare_many_all_success(monkeypatch, tmp_path, capsys):
    # Another scenario: both runs evaluated and resolved the same single id -> all ✅ and success rates 1.00
    p1 = tmp_path / "alpha" / "s.txt"
    p2 = tmp_path / "beta" / "s.txt"

    def fake_get_submitted(path: Path):
        return ["x"]

    def fake_get_resolved(path: Path):
        return ["x"]

    monkeypatch.setattr(cr, "get_submitted", fake_get_submitted, raising=False)
    monkeypatch.setattr(cr, "get_resolved", fake_get_resolved, raising=False)

    cr.compare_many([p1, p2])

    out = capsys.readouterr().out

    # Both runs should show a single ✅ each and success rates 1.00
    assert out.count("✅") >= 2
    assert "1.00" in out
    assert "alpha" in out
    assert "beta" in out
