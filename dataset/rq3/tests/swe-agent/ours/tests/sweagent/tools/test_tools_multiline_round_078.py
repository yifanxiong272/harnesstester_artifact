import re
from types import SimpleNamespace
from sweagent.tools.tools import ToolHandler


def _make_handler(config_endings, submit_command, patterns):
    """Create a ToolHandler instance without running __init__ and inject minimal attributes.

    This avoids interacting with ToolConfig or other initialization logic and keeps tests
    deterministic.
    """
    h = object.__new__(ToolHandler)
    # config only needs the two attributes referenced by _get_first_multiline_cmd
    h.config = SimpleNamespace(
        multi_line_command_endings=set(config_endings),
        submit_command=submit_command,
    )
    # _command_patterns is expected to be a mapping of key -> compiled regex
    h._command_patterns = patterns
    return h


def test_no_match_round_078():
    # Patterns exist but none match the action -> should return None (covers len(matches)==0 branch)
    patterns = {
        "CMD1": re.compile(r"^CMD1:\\s*(.*)$", re.MULTILINE),
        "SUB": re.compile(r"^/submit\\b", re.MULTILINE),
        "OTHER": re.compile(r"will_never_match", re.MULTILINE),
    }
    handler = _make_handler(config_endings=["CMD1"], submit_command="SUB", patterns=patterns)

    action = "this action contains no commands"
    result = handler._get_first_multiline_cmd(action)

    assert result is None


def test_first_of_multiple_matches_round_078():
    # Two patterns that both match; ensure the earliest-starting match is returned.
    pat_a = re.compile(r"cmdA")
    pat_b = re.compile(r"cmdB")

    # Intentionally include an extra pattern that should be filtered out by the comprehension
    patterns = {
        "A": pat_a,
        "B": pat_b,
        "IGNORED": re.compile(r"nothing", re.MULTILINE),
    }

    # Both keys A and B are included in multi_line_command_endings so both will be tested
    handler = _make_handler(config_endings=["A", "B"], submit_command="SUBMIT_KEY", patterns=patterns)

    # Place cmdB later in the string so cmdA is the earliest match
    action = "prefix cmdA somewhere later cmdB end"

    match = handler._get_first_multiline_cmd(action)

    assert match is not None
    # The earliest match should correspond to 'cmdA' which starts at index of its occurrence
    assert match.group(0) == "cmdA"
    assert match.start() == action.index("cmdA")
