# file: sweagent/agent/action_sampler.py:306-314
# asked: {"lines": [308, 309, 310, 311, 312, 313, 314], "branches": [[309, 310], [309, 311], [311, 312], [311, 313]]}
# gained: {"lines": [308, 309, 310, 311, 312, 313, 314], "branches": [[309, 310], [309, 311], [311, 312], [311, 313]]}

import pytest
from sweagent.agent.action_sampler import BinaryTrajectoryComparison

class DummyLogger:
    def __init__(self):
        self.warning_calls = []

    def warning(self, msg, *args):
        # mimic logging.Logger.warning signature
        self.warning_calls.append((msg, args))

def make_instance_with_logger():
    # create instance without calling __init__
    inst = object.__new__(BinaryTrajectoryComparison)
    inst._logger = DummyLogger()
    return inst

def test_interpret_returns_zero_for_first():
    inst = make_instance_with_logger()
    # last line contains 'first' (case-insensitive)
    response = "Some analysis\nI choose the FIRST option."
    result = inst.interpret(response)
    assert result == 0
    # no warning should have been logged
    assert inst._logger.warning_calls == []

def test_interpret_returns_one_for_second():
    inst = make_instance_with_logger()
    response = "analysis\n    the second one is better  "
    result = inst.interpret(response)
    assert result == 1
    assert inst._logger.warning_calls == []

def test_interpret_logs_and_defaults_when_unparseable():
    inst = make_instance_with_logger()
    response = "This is ambiguous.\nI cannot decide between them."
    result = inst.interpret(response)
    # when neither 'first' nor 'second' present, it should log a warning and return 0
    assert result == 0
    assert len(inst._logger.warning_calls) == 1
    msg, args = inst._logger.warning_calls[0]
    assert "Could not interpret response" in msg
    # ensure the logged args include the original response as %s formatting would expect
    # depending on implementation, the response may be passed as an arg tuple
    if args:
        # args is a tuple; first element should be the response
        assert args[0] == response
