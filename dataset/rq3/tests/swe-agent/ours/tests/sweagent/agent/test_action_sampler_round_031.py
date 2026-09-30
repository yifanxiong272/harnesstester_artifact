import pytest
from sweagent.agent.action_sampler import BinaryTrajectoryComparison
from sweagent.exceptions import FormatError


class RecordingLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg, *args):
        # store the formatted tuple for later assertions
        self.warnings.append((msg, args))


class ToolsAlwaysFail:
    def parse_actions(self, completion):
        # Always fail to simulate unparseable completions
        raise FormatError("parse failed")


class ToolsSelective:
    def __init__(self, fail_on_key="bad"):
        self.fail_on_key = fail_on_key

    def parse_actions(self, completion):
        # If the completion contains the configured key, raise to simulate parse failure
        if isinstance(completion, dict) and self.fail_on_key in completion:
            raise FormatError("selective parse failure")
        # otherwise succeed (no return needed)
        return None


def make_btc_with(tools, logger=None):
    # Create BinaryTrajectoryComparison instance without invoking its real __init__
    inst = object.__new__(BinaryTrajectoryComparison)
    inst._tools = tools
    inst._logger = logger or RecordingLogger()
    return inst


def test_filter_parseable_completions_all_unparseable_round_031():
    # All completions are unparseable -> should raise FormatError with expected message
    completions = [{"a": 1}, {"b": 2}]
    tools = ToolsAlwaysFail()
    logger = RecordingLogger()
    btc = make_btc_with(tools, logger)

    with pytest.raises(FormatError) as exc:
        btc.filter_parseable_completions(completions)

    # The function raises with the exact message defined in the implementation
    assert str(exc.value) == "No completions could be parsed."

    # Logger should have recorded a warning for each unparseable completion
    assert len(logger.warnings) == 2
    # Verify the warning message template and that the completion objects were passed through
    assert logger.warnings[0][0] == "Could not parse completion %s, skipping."
    assert logger.warnings[0][1] == (completions[0],)
    assert logger.warnings[1][1] == (completions[1],)


def test_filter_parseable_completions_some_parseable_round_031():
    # Some completions parse, some do not -> should return only the parseable ones
    completions = [{"ok": True}, {"bad": True}, {"ok2": 1}]
    tools = ToolsSelective(fail_on_key="bad")
    logger = RecordingLogger()
    btc = make_btc_with(tools, logger)

    result = btc.filter_parseable_completions(completions)

    # Should have filtered out only the completion that caused parse failure
    assert result == [{"ok": True}, {"ok2": 1}]

    # Logger should have exactly one warning for the failing completion
    assert len(logger.warnings) == 1
    assert logger.warnings[0][1] == (completions[1],)
