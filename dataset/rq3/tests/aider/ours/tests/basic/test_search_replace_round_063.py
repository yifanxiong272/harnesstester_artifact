import pytest

from aider.coders.search_replace import RelativeIndenter


def test_make_absolute_simple_accumulate_round_063():
    # Two pairs: indent accumulates when dent does not start with marker
    ri = RelativeIndenter([])

    text = (
        "    \n"  # dent 1: 4 spaces
        "line1\n"  # content 1
        "  \n"      # dent 2: 2 spaces
        "line2\n"  # content 2
    )

    # Expected: first line indented by 4, second by prev_indent + 2 -> 6 spaces
    expected = "    line1\n" + "      line2\n"
    assert ri.make_absolute(text) == expected


def test_make_absolute_outdent_with_marker_round_063():
    # When a dent startswith the marker, it outdents by removing characters
    ri = RelativeIndenter([])
    marker = ri.marker
    # First iteration creates a prev_indent of 4 spaces; second uses marker to outdent
    text = (
        "    \n"           # dent 1
        "A\n"               # content 1
        f"{marker}{marker}\n"  # dent 2: two marker chars -> outdent length 2
        "B\n"               # content 2
    )

    # After outdenting, prev_indent (4 spaces)[:-2] => 2 spaces
    expected = "    A\n" + "  B\n"
    assert ri.make_absolute(text) == expected


def test_make_absolute_blank_line_preserved_round_063():
    # If the content line is blank (just a newline), it should be preserved verbatim
    ri = RelativeIndenter([])

    text = (
        "  \n"  # dent line
        "\n"    # blank content line -> should be preserved as-is
    )

    assert ri.make_absolute(text) == "\n"


def test_make_absolute_raises_when_marker_in_result_round_063():
    # If the final joined result contains the marker, a ValueError is raised
    ri = RelativeIndenter([])
    marker = ri.marker

    # Content contains the marker, which should cause make_absolute to raise
    text = (
        "  \n"  # dent
        f"contains{marker}\n"  # content includes marker
    )

    with pytest.raises(ValueError, match="Error transforming text back to absolute indents"):
        ri.make_absolute(text)
