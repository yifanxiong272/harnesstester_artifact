import pytest
from sweagent.tools.utils import _guard_multiline_input


class FakeMatch:
    """A tiny fake match object that mimics the re.Match API used by the function under test."""

    def __init__(self, start: int, end: int, eof: str):
        self._start = start
        self._end = end
        self._eof = eof

    def start(self) -> int:
        return self._start

    def end(self) -> int:
        return self._end

    def group(self, n: int):
        if n == 3:
            return self._eof
        raise IndexError("Only group 3 is supported in this fake match")


def test_modify_guarded_round_026():
    """
    Case: there is a pre_action (non-empty) and a matched multiline block whose
    first line does NOT already end with << 'EOF'. This exercises the branch
    that inserts the heredoc marker. Note: the implementation slices the
    match_action again using the absolute start index which causes the first
    few characters of the original match_action to be dropped in the result.
    The test asserts the exact, observable behavior.
    """
    pre = "PRE"
    match_body = "command\nline2\nEND\n"
    rem = pre + match_body

    def match_fct(text: str):
        # find the leading 'command' marker and create a FakeMatch that spans
        # from that position to the end of the remaining text
        idx = text.find("command")
        if idx != -1:
            return FakeMatch(idx, len(text), "END")
        return None

    out = _guard_multiline_input(rem, match_fct)

    # Expected observed behavior given the source code's slicing logic:
    # pre_action is "PRE"; match_action is "command\nline2\nEND\n";
    # guarded_command = match_action[first_match.start():] where start==3 ->
    # match_action[3:] == "mand\nline2\nEND\n" -> first_line == "mand" ->
    # becomes "mand << 'END'\nline2\nEND\n". The final join uses a newline
    # between pre and this modified guarded_command.
    expected = "PRE\n" + "mand << 'END'\nline2\nEND\n"

    assert out == expected


def test_already_guarded_round_026():
    """
    Case: matched block already has the heredoc marker on the first line.
    The code should append the match_action as-is (else branch of the inner if).
    This exercises the branch where first_match.start() is 0 (no pre_action).
    """
    match_action = "command << 'END'\nline2\nEND\n"
    rem = match_action

    def match_fct(text: str):
        idx = text.find("command")
        if idx != -1:
            return FakeMatch(idx, len(text), "END")
        return None

    out = _guard_multiline_input(rem, match_fct)

    # The match starts at 0 and the first line already ends with << 'END', so
    # the function should append the match_action unchanged.
    assert out == match_action


def test_no_match_appends_whole_round_026():
    """
    Case: match_fct returns None. The function should append the entire
    remaining action and return it unchanged.
    """
    rem = "this has no matches"

    def match_fct(text: str):
        return None

    out = _guard_multiline_input(rem, match_fct)
    assert out == rem


def test_match_with_only_whitespace_round_026():
    """
    Case: there is a pre_action and the match_action is only whitespace.
    match_action.strip() will be False causing the inner guarded block to be
    skipped. The observable result should only include the pre_action.
    """
    pre = "PRE"
    whitespace_block = "   \n"
    rem = pre + whitespace_block

    def match_fct(text: str):
        idx = text.find(whitespace_block)
        if idx != -1:
            return FakeMatch(idx, len(text), "")
        return None

    out = _guard_multiline_input(rem, match_fct)

    # Since match_action.strip() is False, only the pre_action should be in
    # parsed_action.
    assert out == pre
