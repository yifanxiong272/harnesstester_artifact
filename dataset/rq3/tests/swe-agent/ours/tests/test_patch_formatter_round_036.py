import pytest

from sweagent.utils.patch_formatter import PatchFormatter


def test_format_file_single_hunk_with_above_and_below_linenos_round_036():
    text = "\n".join([f"line{i}" for i in range(1, 7)])  # 6 lines
    # Provide an empty patch string and a benign read_method to avoid PatchSet(None) errors
    pf = PatchFormatter("", lambda path: "")

    # single hunk starting at 2, stopping at 4 -> above (1 line) and below (2 lines)
    res = pf.format_file(text, [2], [4], linenos=True)

    expected = "[1 lines above omitted]\n" + "\n".join([f"{i:6d}: line{i}" for i in (2, 3)]) + "\n[2 lines below omitted]"
    assert res == expected


def test_format_file_two_hunks_with_omitted_gap_and_no_linenos_round_036():
    # 5 lines total; two hunks with a 1-line gap between them
    lines = ["l1", "l2", "l3", "l4", "l5"]
    text = "\n".join(lines)
    pf = PatchFormatter("", lambda path: "")

    # hunks: [1:2) -> l1 ; [3:5) -> l3 and l4 ; gap of 1 between them
    res = pf.format_file(text, [1, 3], [2, 5], linenos=False)

    expected = "l1\n\n[1 lines omitted]\n\nl3\nl4"
    assert res == expected


def test_format_file_two_hunks_zero_omitted_between_round_036():
    # 5 lines; two consecutive hunks where the second starts exactly at the previous stop
    lines = ["l1", "l2", "l3", "l4", "l5"]
    text = "\n".join(lines)
    pf = PatchFormatter("", lambda path: "")

    # hunks: [1:3) -> l1-l2 ; [3:5) -> l3-l4 ; no omitted lines between (n_omitted == 0)
    res = pf.format_file(text, [1, 3], [3, 5], linenos=True)

    expected = (
        f"{1:6d}: l1\n{2:6d}: l2\n{3:6d}: l3\n{4:6d}: l4"
    )
    assert res == expected


def test_format_file_empty_starts_returns_empty_round_036():
    pf = PatchFormatter("", lambda path: "")
    assert pf.format_file("any text", [], []) == ""
