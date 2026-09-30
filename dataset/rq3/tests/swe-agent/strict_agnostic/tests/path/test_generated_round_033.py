import pytest

from sweagent.exceptions import FormatError
from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class LoggerFake:
    def __init__(self):
        self.warnings = []

    def warning(self, msg, *args):
        # record invocation for assertions
        self.warnings.append((msg, args))


class DummyToolsAllGood:
    def parse_actions(self, completion):
        # Always parse successfully
        return True


class DummyToolsSomeBad:
    def __init__(self, bad_marker="bad"):
        self.bad_marker = bad_marker

    def parse_actions(self, completion):
        # Raise FormatError for completions marked as bad
        if completion.get(self.bad_marker):
            raise FormatError("parse failure")
        return True


class DummyToolsAllBad:
    def parse_actions(self, completion):
        # Always fail to parse
        raise FormatError("always fail")


def make_sampler_with_tools(tools):
    # Avoid calling BinaryTrajectoryComparison.__init__ to keep tests focused and deterministic.
    sampler = object.__new__(BinaryTrajectoryComparison)
    sampler._tools = tools
    sampler._logger = LoggerFake()
    return sampler


def test_filter_parseable_completions_all_parse_round_033():
    """
    When all completions parse successfully, the method should return the full list unchanged.
    Covers lines where parse_actions does not raise and filtered_completions is appended.
    """
    tools = DummyToolsAllGood()
    sampler = make_sampler_with_tools(tools)

    completions = [{"id": 1}, {"id": 2}]
    result = sampler.filter_parseable_completions(completions)

    # Should return the same elements in the same order
    assert result == completions


def test_filter_parseable_completions_some_fail_round_033():
    """
    When some completions fail to parse, those are skipped and a logger warning is emitted.
    This exercises the except FormatError branch and the continue behavior.
    """
    tools = DummyToolsSomeBad(bad_marker="bad")
    sampler = make_sampler_with_tools(tools)

    good = {"id": "good"}
    bad = {"id": "bad", "bad": True}
    completions = [bad, good]

    result = sampler.filter_parseable_completions(completions)

    # Only the good completion should remain
    assert result == [good]

    # Logger should have recorded a warning about the skipped completion
    assert len(sampler._logger.warnings) == 1
    msg, args = sampler._logger.warnings[0]
    assert "Could not parse completion" in msg
    # The logged argument should include the bad completion we expected to be skipped
    assert args[0] == bad


def test_filter_parseable_completions_none_parse_raises_round_033():
    """
    When no completions can be parsed at all, the method should raise FormatError with
    the expected message. This exercises the branch that raises when filtered_completions
    is empty.
    """
    tools = DummyToolsAllBad()
    sampler = make_sampler_with_tools(tools)

    completions = [{"id": 1}, {"id": 2}]

    with pytest.raises(FormatError) as excinfo:
        sampler.filter_parseable_completions(completions)

    # The message should match the one raised in the implementation
    assert str(excinfo.value) == "No completions could be parsed."
