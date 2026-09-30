import pytest
from pathlib import Path
from aider.coders import search_replace as sr


def test_proc_various_round_009(tmp_path, monkeypatch):
    """
    Exercise proc() with three deterministic preprocessor combinations.

    - First preproc returns None -> should become 'fail' and not write a file.
    - Second preproc returns a truthy non-matching string -> should be written and marked 'WRONG'.
    - Third preproc returns the exact 'correct' text -> should be written and marked 'pass'.

    This covers the method-name suffix logic, the write/unlink branches, and the
    pass/WRONG/fail result conversions.
    """
    # Prepare directory with required input files
    d = tmp_path
    (d / "search").write_text("SEARCH")
    (d / "replace").write_text("REPLACE")
    (d / "original").write_text("ORIG")
    # The expected correct content for one strategy
    (d / "correct").write_text("CORRECT")

    # Define deterministic preprocs to trigger different method-name suffixes:
    # (strip_blank, rel_indent, rev_lines)
    preprocs = [
        (False, False, False),  # base -> method 'dmpl' -> returns None -> 'fail'
        (True, False, False),   # strip_blank -> method 'dmpl_s' -> returns 'X' -> 'WRONG'
        (False, True, True),    # rel_indent+rev_lines -> method 'dmpl_ir' -> returns 'CORRECT' -> 'pass'
    ]

    # Monkeypatch the module's all_preprocs so proc() will iterate our list
    monkeypatch.setattr(sr, "all_preprocs", preprocs)

    # Deterministic replacement for try_strategy to avoid heavy logic / external deps
    def fake_try_strategy(texts, strategy, preproc):
        # Return values chosen to exercise 'fail', 'WRONG', and 'pass' branches
        if preproc == (False, False, False):
            return None
        if preproc == (True, False, False):
            return "X"
        if preproc == (False, True, True):
            return "CORRECT"
        return None

    monkeypatch.setattr(sr, "try_strategy", fake_try_strategy)

    # Create an existing file for the third method to force the unlink branch
    # The target filename is original.<method>, method for third preproc will be 'dmpl_ir'
    (d / "original.dmpl_ir").write_text("OLD")

    # Run proc and capture results
    results = sr.proc(str(d))

    # The order is determined by insertion order of preprocs -> dict insertion order
    expected = [("dmpl", "fail"), ("dmpl_s", "WRONG"), ("dmpl_ir", "pass")]
    assert results == expected

    # Check file existence and contents according to the three cases
    # 1) 'dmpl' -> None -> no file created
    assert not (d / "original.dmpl").exists()

    # 2) 'dmpl_s' -> written with content 'X' and marked WRONG
    assert (d / "original.dmpl_s").exists()
    assert (d / "original.dmpl_s").read_text() == "X"

    # 3) 'dmpl_ir' -> original.dmpl_ir existed and should have been unlinked then re-written
    assert (d / "original.dmpl_ir").exists()
    assert (d / "original.dmpl_ir").read_text() == "CORRECT"
