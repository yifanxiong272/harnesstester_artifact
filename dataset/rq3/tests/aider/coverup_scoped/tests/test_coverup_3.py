# file: aider/coders/search_replace.py:622-690
# asked: {"lines": [623, 625, 626, 627, 628, 629, 630, 634, 636, 641, 644, 645, 646, 647, 648, 649, 652, 653, 654, 655, 656, 658, 659, 660, 661, 662, 663, 664, 665, 666, 668, 669, 671, 672, 673, 674, 675, 677, 678, 680, 681, 682, 684, 686, 688, 690], "branches": [[653, 654], [653, 671], [654, 653], [654, 655], [659, 660], [659, 661], [661, 662], [661, 663], [663, 664], [663, 665], [665, 666], [665, 668], [672, 673], [672, 690], [674, 675], [674, 677], [677, 678], [677, 686], [681, 682], [681, 684]]}
# gained: {"lines": [623, 625, 626, 627, 628, 629, 630, 634, 636, 641, 644, 645, 646, 647, 648, 649, 652, 653, 654, 655, 656, 658, 659, 660, 661, 662, 663, 664, 665, 666, 668, 669, 671, 672, 673, 674, 675, 677, 678, 680, 681, 682, 684, 686, 688, 690], "branches": [[653, 654], [653, 671], [654, 653], [654, 655], [659, 660], [659, 661], [661, 662], [661, 663], [663, 664], [663, 665], [665, 666], [665, 668], [672, 673], [672, 690], [674, 675], [674, 677], [677, 678], [677, 686], [681, 682], [681, 684]]}

import os
from pathlib import Path
import pytest

from aider.coders import search_replace as sr


def test_proc_various_outcomes(tmp_path, monkeypatch):
    # Prepare directory and files
    d = tmp_path
    (d / "search").write_text("s")
    (d / "replace").write_text("r")
    (d / "original").write_text("o")
    correct_content = "CORRECT_CONTENT"
    (d / "correct").write_text(correct_content)

    # Ensure dmp_lines_apply has the expected name
    def dmp_lines_apply(*args, **kwargs):
        return None

    # Define preprocs to generate different method names:
    # (False, False, False) -> "dmpl" -> return falsy -> "fail" (no file)
    # (True, False, False)  -> "dmpl_s" -> return wrong content -> "WRONG" (file written)
    # (False, True, True)   -> "dmpl_ir" -> return correct content -> "pass" (file written)
    preprocs = [
        (False, False, False),
        (True, False, False),
        (False, True, True),
    ]

    # Monkeypatch module attributes used by proc
    monkeypatch.setattr(sr, "dmp_lines_apply", dmp_lines_apply)
    monkeypatch.setattr(sr, "all_preprocs", preprocs)

    # Make read_text simply read from the Path given
    monkeypatch.setattr(sr, "read_text", lambda p: Path(p).read_text())

    # Pre-create a file that should be unlinked by proc for "dmpl_s"
    preexisting = d / "original.dmpl_s"
    preexisting.write_text("OLD")

    # Define try_strategy behavior based on preproc tuple
    def try_strategy(texts, strategy, preproc):
        if preproc == (False, False, False):
            return ""  # falsy -> results in 'fail' and no file written
        if preproc == (True, False, False):
            return "WRONG_CONTENT"
        if preproc == (False, True, True):
            return correct_content
        return None

    monkeypatch.setattr(sr, "try_strategy", try_strategy)

    # Call proc and capture results
    results = sr.proc(d)

    # Expect order corresponds to preprocs order
    expected = [("dmpl", "fail"), ("dmpl_s", "WRONG"), ("dmpl_ir", "pass")]
    assert results == expected

    # Check files: dmpl should not exist, dmpl_s and dmpl_ir should exist
    assert not (d / "original.dmpl").exists()
    assert (d / "original.dmpl_s").exists()
    assert (d / "original.dmpl_ir").exists()

    # Validate contents
    assert (d / "original.dmpl_s").read_text() == "WRONG_CONTENT"
    assert (d / "original.dmpl_ir").read_text() == correct_content


def test_proc_missing_files_returns_none(tmp_path, monkeypatch):
    # Simulate read_text raising FileNotFoundError to hit the except branch
    def raise_not_found(path):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(sr, "read_text", raise_not_found)

    res = sr.proc(tmp_path)
    assert res is None
