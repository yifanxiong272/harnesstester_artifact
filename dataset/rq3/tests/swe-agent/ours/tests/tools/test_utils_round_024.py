import re
from sweagent.tools.utils import _guard_multiline_input


class DummyMatch:
    """Minimal stand-in for a re.Match-like object used by _guard_multiline_input.

    Provides start(), end(), group(3) and truthiness. The implementation is
    intentionally small and deterministic for testing the logic in the target
    function without relying on regexes or external state.
    """

    def __init__(self, start: int, end: int, group3: str):
        self._start = start
        self._end = end
        self._group3 = group3

    def start(self) -> int:
        return self._start

    def end(self) -> int:
        return self._end

    def group(self, idx: int):
        if idx == 3:
            return self._group3
        raise IndexError("Unsupported group index")

    def __bool__(self):
        return True


def test_guard_multiline_add_heredoc_round_024():
    """When a single multiline block is present and its first line lacks the
    heredoc marker, the function must append " << '{eof}'" to that first line
    and return that guarded block as the only element.
    """

    # Build a rem_action that is entirely the multiline command; match covers all
    rem_action = """cmd
line1
line2
END
"""

    # match covers the whole string and group(3) yields EOF marker 'END'
    def match_fct(text: str):
        if text == rem_action:
            return DummyMatch(0, len(text), "END")
        return None

    out = _guard_multiline_input(rem_action, match_fct)

    # Expected: first line appended with << 'END', rest unchanged
    expected = """cmd << 'END'
line1
line2
END
"""
    assert out == expected


def test_guard_multiline_preserve_existing_heredoc_and_pre_round_024():
    """When there's a pre_action and then a multiline block whose first line
    already ends with the heredoc marker, the function must preserve both the
    pre_action and the matched block and then append any trailing remainder.
    This verifies the branch that skips adding another "<< 'eof'".
    """

    pre = "pre\n"
    match_text = "cmd << 'EOF'\nbody\nEOF\n"
    rem_action = pre + match_text + "trailing"

    def match_fct(text: str):
        # Only match when the block is present; compute start/end deterministically
        needle = "cmd << 'EOF'"
        idx = text.find(needle)
        if idx == -1:
            return None
        start = idx
        end = idx + len(match_text)
        return DummyMatch(start, end, "EOF")

    out = _guard_multiline_input(rem_action, match_fct)

    # The function appends list elements and then joins with '\n'. Because the
    # pre and match_text contain newlines, the join will introduce single
    # newline separators between elements; construct the exact expected string.
    expected = pre + "\n" + match_text + "\n" + "trailing"
    # Normalize expectation build to the exact join behavior in the implementation
    # The function constructs parsed_action = [pre, match_text, 'trailing'] and
    # returns "\n".join(parsed_action)
    expected_joined = "\n".join([pre, match_text, "trailing"])  # deterministic

    assert out == expected_joined
