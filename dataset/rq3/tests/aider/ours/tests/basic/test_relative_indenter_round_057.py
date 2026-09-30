import pytest

from aider.coders.search_replace import RelativeIndenter


def test_make_relative_various_indent_round_057():
    """Exercise increase, same, and decrease indent transitions.

    The test builds a 4-line input with indents: 4, 8, 8, 4 spaces.
    This triggers change>0 (first and second transitions), change==0 (third),
    and change<0 (fourth). We assert the exact transformed output using the
    instance's chosen marker so the test remains deterministic even if the
    implementation selects a non-default marker.
    """
    text = "    A\n        B\n        C\n    D\n"

    ri = RelativeIndenter([text])
    # Confirm the constructor chose a marker deterministically (not None)
    assert isinstance(ri.marker, str) and len(ri.marker) >= 1

    res = ri.make_relative(text)

    # Build expected output in the same way the function composes it:
    # 1) first line: indent (4 spaces) then newline then content
    # 2) second line: 4-space cur_indent then newline then content
    # 3) third line: no cur_indent -> just a leading newline then content
    # 4) fourth line: outdent represented by marker repeated 4 times, newline, content
    expected = (
        "    \n"  # first line indent preserved as separate line
        "A\n"
        "    \n"  # second line cur_indent of 4 spaces
        "B\n"
        "\n"     # third line produced an empty cur_indent, resulting in an extra leading newline
        "C\n"
        f"{ri.marker * 4}\n"  # outdent marker repeated 4 times
        "D\n"
    )

    assert res == expected


def test_make_relative_raises_if_marker_in_text_round_057():
    """When the provided text already contains the indenter's marker,
    make_relative must raise a ValueError with a helpful message.
    """
    # Choose constructor input that does NOT contain the default arrow marker so
    # the marker will be the default ARROW (or at least deterministic for our instance).
    ri = RelativeIndenter(["no arrow here"])
    # Build a text that includes the instance marker to trigger the early error.
    bad_text = f"start{ri.marker}end"

    with pytest.raises(ValueError) as excinfo:
        ri.make_relative(bad_text)

    assert "outdent marker" in str(excinfo.value)
