# file: aider/coders/search_replace.py:106-138
# asked: {"lines": [111, 112, 114, 116, 117, 118, 119, 121, 122, 123, 124, 125, 126, 127, 129, 131, 134, 135, 137, 138], "branches": [[111, 112], [111, 114], [118, 119], [118, 137], [124, 125], [124, 126], [126, 127], [126, 129]]}
# gained: {"lines": [111, 112, 114, 116, 117, 118, 119, 121, 122, 123, 124, 125, 126, 127, 129, 131, 134, 135, 137, 138], "branches": [[111, 112], [111, 114], [118, 119], [118, 137], [124, 125], [124, 126], [126, 127], [126, 129]]}

import pytest
from aider.coders.search_replace import RelativeIndenter

def test_make_relative_positive_zero_negative_changes():
    # Prepare a text with increasing indent, same indent, decreasing indent, and no indent
    text = (
        "    Foo\n"        # +4 (from 0 -> 4)  -> positive
        "        Bar\n"    # +4 (from 4 -> 8)  -> positive
        "        Baz\n"    #  0 (8 -> 8)       -> zero
        "    Fob\n"        # -4 (8 -> 4)       -> negative
        "NoIndent\n"       # -4 (4 -> 0)       -> negative
    )

    indenter = RelativeIndenter([""])  # ensure default marker '←' is chosen
    assert indenter.marker == "←"

    res = indenter.make_relative(text)

    # Build expected result step by step according to the algorithm
    expected = (
        "    \nFoo\n"      # first line (4 spaces -> positive): "    " + "\n" + "Foo\n"
        "    \nBar\n"      # second line (8 -> 4 change): last 4 spaces + "\n" + "Bar\n"
        "\nBaz\n"          # third line (8 -> 8 change 0): "" + "\n" + "Baz\n"
        "←←←←\nFob\n"       # fourth line (4 -> negative 4): marker*4 + "\n" + "Fob\n"
        "←←←←\nNoIndent\n"  # fifth line (0 -> negative 4): marker*4 + "\n" + "NoIndent\n"
    )

    assert res == expected

def test_make_relative_raises_if_marker_in_text():
    indenter = RelativeIndenter([""])  # default marker '←'
    text_with_marker = "some line\ncontains arrow ← here\nanother line\n"
    with pytest.raises(ValueError) as exc:
        indenter.make_relative(text_with_marker)
    assert f"Text already contains the outdent marker: {indenter.marker}" in str(exc.value)
