import io
import sys
import pytest
from aider.coders import search_replace

# Ensure deterministic iteration instead of progress bars

def test_main_single_pass_round_023(monkeypatch, capsys):
    """Single directory with one method that returns 'pass'.

    Exercises: loop over dnames, building methods list, results_matrix population,
    header + single-row printing, and colorization path where colorized length == res length.
    """
    # Make tqdm identity for deterministic iteration
    monkeypatch.setattr(search_replace, "tqdm", lambda x: x)

    # Fake proc always returns a single method 'm1' with result 'pass'
    def fake_proc(dname):
        # ensure we receive a Path-like string representation
        assert str(dname)  # deterministic check that main passes something
        return [("m1", "pass")]

    monkeypatch.setattr(search_replace, "proc", fake_proc)

    # Colorize returns uppercase PASS (same length as 'pass') to hit stable formatting
    monkeypatch.setattr(search_replace, "colorize_result", lambda r: r.upper())

    # Run main with one directory name
    search_replace.main(["dirA"])

    out = capsys.readouterr().out

    # Oracles: header, method name, directory name and the colorized result must appear
    assert "Directory" in out
    assert "m1" in out
    assert "dirA" in out
    assert "PASS" in out


def test_main_multiple_methods_round_023(monkeypatch, capsys):
    """Multiple directories and methods exercising pass_counts sorting and varied colorized lengths.

    This test verifies directories are sorted by decreasing number of 'pass' results and
    that different colorized outputs appear in the printed rows.
    """
    monkeypatch.setattr(search_replace, "tqdm", lambda x: x)

    # proc returns different results depending on the directory name passed in
    def fake_proc(dname):
        name = str(dname)
        if name == "d1":
            # d1: one pass, one fail
            return [("m1", "fail"), ("m2", "pass")]
        elif name == "d2":
            # d2: two passes
            return [("m1", "pass"), ("m2", "pass")]
        else:
            return []

    monkeypatch.setattr(search_replace, "proc", fake_proc)

    # colorize_result emits clearly distinguishable strings (different lengths)
    def fake_colorize(res):
        if res == "pass":
            return f"[OK:{res}]"  # length > original 'pass'
        return f"({res})"  # length > original 'fail'

    monkeypatch.setattr(search_replace, "colorize_result", fake_colorize)

    # Provide two directories; ordering should be d2 first (2 passes) then d1 (1 pass)
    search_replace.main(["d1", "d2"])

    out = capsys.readouterr().out

    # Header contains both methods
    assert "m1" in out and "m2" in out

    # Ensure both directory rows printed and that d2 comes before d1 due to pass_counts
    idx_d2 = out.find("d2")
    idx_d1 = out.find("d1")
    assert idx_d2 != -1 and idx_d1 != -1 and idx_d2 < idx_d1

    # Ensure colorized outputs are present for pass and fail
    assert "[OK:pass]" in out
    assert "(fail)" in out
