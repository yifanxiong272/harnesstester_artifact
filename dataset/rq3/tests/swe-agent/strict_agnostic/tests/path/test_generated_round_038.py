import pytest
from sweagent.utils.patch_formatter import PatchFormatter


def test_above_omitted_round_038():
    """When the requested hunk does not start at line 1, the formatter
    should include a top omitted marker and a bottom omitted marker when
    the hunk does not cover the entire file. Also verifies the lineno
    formatting branch (linenos=True).
    """
    # PatchFormatter expects a patch-like input for its first arg that is
    # consumable by unidiff.PatchSet. Passing an empty string is accepted;
    # passing None leads to a TypeError in unidiff.PatchSet.
    pf = PatchFormatter("", lambda path: "")
    # Create a 5-line file and request only line 3 (start=3, stop=4).
    text = "\n".join([f"line{i}" for i in range(1, 6)])
    out = pf.format_file(text, [3], [4])

    # Top omitted marker should reflect 2 lines above omitted
    assert "[2 lines above omitted]" in out
    # Numbered line for the single returned line should be present (formatted width 6)
    assert "     3: line3" in out
    # Bottom omitted marker should reflect 1 line below omitted
    assert "[1 lines below omitted]" in out


def test_between_hunks_no_linenos_round_038():
    """When there are two hunks separated by omitted lines, the formatter
    should include an in-between omitted marker. Also test the linenos=False
    branch where raw lines (no numbering) are returned.
    """
    pf = PatchFormatter("", lambda path: "")
    # 6-line file. Two hunks: first returns line1, second returns lines 4 and 5
    text = "\n".join([f"line{i}" for i in range(1, 7)])
    out = pf.format_file(text, [1, 4], [2, 6], linenos=False)

    # First hunk content should appear at the top (no numbering)
    assert out.startswith("line1")
    # There should be an omitted marker for the 2 lines between the hunks
    assert "[2 lines omitted]" in out
    # The second hunk should contain the two requested lines (4 and 5)
    assert "line4\nline5" in out


def test_adjacent_hunks_linenos_round_038():
    """Adjacent hunks (where start == last_stop) should not emit an omitted
    in-between marker. Verify both hunks are emitted and numbered.
    This hits the branch where n_omitted == 0. Use a file length such that
    there is no trailing omitted marker.
    """
    pf = PatchFormatter("", lambda path: "")
    # 3-line file. Two adjacent hunks: first returns line1, second returns line2.
    text = "\n".join(["a", "b", "c"])  # lines: a,b,c
    out = pf.format_file(text, [1, 2], [2, 3])

    # Both lines should be present and numbered (linenos default True)
    assert "     1: a" in out
    assert "     2: b" in out
    # There should be no in-between "lines omitted" marker
    assert "lines omitted" not in out
