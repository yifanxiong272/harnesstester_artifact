import pytest

from sweagent.agent.action_sampler import BinaryTrajectoryComparison


class DummyLogger:
    def __init__(self):
        self.calls = []

    def warning(self, msg, *args, **kwargs):
        # record the raw message template and arguments to assert later
        self.calls.append((msg, args, kwargs))


def _make_instance_with_logger():
    # Instantiate without calling __init__ to avoid needing full collaborator objects.
    inst = BinaryTrajectoryComparison.__new__(BinaryTrajectoryComparison)
    inst._logger = DummyLogger()
    # config attribute may be accessed elsewhere; set a benign placeholder
    inst.config = object()
    return inst


def test_interpret_returns_0_for_first_round_048():
    inst = _make_instance_with_logger()
    # last line contains the word 'first' in mixed case and surrounding text
    response = "Some evaluation text\nI think the FIRST option is better"
    result = inst.interpret(response)
    assert result == 0
    # no warning should have been emitted for a successful interpretation
    assert inst._logger.calls == []


def test_interpret_returns_1_for_second_round_048():
    inst = _make_instance_with_logger()
    # last line contains 'second' lowercased within other text
    response = "analysis summary\nPrefer the second submission based on tests"
    result = inst.interpret(response)
    assert result == 1
    assert inst._logger.calls == []


def test_interpret_warns_and_defaults_to_first_round_048():
    inst = _make_instance_with_logger()
    # last line contains neither 'first' nor 'second'
    response = "analysis summary\nUndetermined — neither option is clear"
    result = inst.interpret(response)
    # default behavior is to choose first (0) and emit a warning
    assert result == 0
    assert len(inst._logger.calls) == 1
    msg_template, args, kwargs = inst._logger.calls[0]
    # message template should indicate inability to interpret
    assert "Could not interpret response" in msg_template
    # the original response should be passed as the first arg
    assert args[0] == response
