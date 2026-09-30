import pytest

# Import the function under test. This import uses the real module so coverage is
# attributed to aider/main.py. The test avoids any network or external IO.
from aider.main import parse_lint_cmds


class DummyIO:
    """Minimal io-like object matching the methods used by parse_lint_cmds.

    Records calls to tool_error and tool_output so tests can assert on them.
    """

    def __init__(self):
        self.errors = []
        self.outputs = []

    def tool_error(self, msg):
        # mimic original signature and record message
        self.errors.append(msg)

    def tool_output(self, msg):
        # mimic original signature and record message
        self.outputs.append(msg)


def test_parse_lint_cmds_with_explicit_languages_round_084():
    io = DummyIO()
    lint_cmds = [
        "python: flake8 --select=E9",
        "js:eslint --fix",
    ]

    res = parse_lint_cmds(lint_cmds, io)

    # No errors or extra outputs should be produced
    assert io.errors == []
    assert io.outputs == []

    # Result must contain the parsed language keys and exact commands (stripped)
    assert isinstance(res, dict)
    assert res.get("python") == "flake8 --select=E9"
    assert res.get("js") == "eslint --fix"
    assert len(res) == 2


def test_parse_lint_cmds_without_language_prefix_round_084():
    io = DummyIO()
    lint_cmds = [
        "   flake8 --select=E9  ",  # no lang prefix -> lang should be None
        "js:  eslint --fix  ",
    ]

    res = parse_lint_cmds(lint_cmds, io)

    # No errors because both entries yield non-empty commands after strip
    assert io.errors == []
    assert io.outputs == []

    # The no-prefix entry is stored under the None key (as implemented)
    assert isinstance(res, dict)
    assert None in res
    assert res[None] == "flake8 --select=E9"
    assert res.get("js") == "eslint --fix"
    assert len(res) == 2


def test_parse_lint_cmds_empty_command_reports_error_round_084():
    io = DummyIO()
    # The lint command has a language prefix but no command -> triggers error branch
    lint_cmds = ["python:"]

    res = parse_lint_cmds(lint_cmds, io)

    # When an error occurs, parse_lint_cmds returns None
    assert res is None

    # tool_error must be called once with the exact formatted message
    assert io.errors == ['Unable to parse --lint-cmd "python:"']

    # tool_output must have been called twice with the exact helper messages
    assert io.outputs == [
        'The arg should be "language: cmd --args ..."',
        'For example: --lint-cmd "python: flake8 --select=E9"',
    ]
