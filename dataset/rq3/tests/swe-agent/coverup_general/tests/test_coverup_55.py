# file: sweagent/agent/action_sampler.py:306-314
# asked: {"lines": [308, 309, 310, 311, 312, 313, 314], "branches": [[309, 310], [309, 311], [311, 312], [311, 313]]}
# gained: {"lines": [308, 309, 310, 311, 312, 313, 314], "branches": [[309, 310], [309, 311], [311, 312], [311, 313]]}

import pytest
from unittest.mock import Mock

from sweagent.agent.action_sampler import BinaryTrajectoryComparison


def _make_instance_with_logger():
    # Create instance without calling __init__
    inst = object.__new__(BinaryTrajectoryComparison)
    inst._logger = Mock()
    return inst


def test_interpret_returns_zero_when_last_line_mentions_first():
    inst = _make_instance_with_logger()
    # last line contains 'first' in mixed case and with surrounding whitespace
    response = "Some context\n  The FIRST option is better   "
    result = inst.interpret(response)
    assert result == 0
    # logger should not be used
    inst._logger.warning.assert_not_called()


def test_interpret_returns_one_when_last_line_mentions_second():
    inst = _make_instance_with_logger()
    response = "irrelevant\nchoose the second\n"
    # Even with trailing newline, last_line logic strips properly
    result = inst.interpret(response)
    assert result == 1
    inst._logger.warning.assert_not_called()


def test_interpret_logs_and_returns_zero_when_unparseable():
    inst = _make_instance_with_logger()
    response = "This response does not indicate a choice.\nNeither option is named."
    result = inst.interpret(response)
    assert result == 0
    # Ensure warning called with exact format string and the original response as argument
    inst._logger.warning.assert_called_once_with(
        "Could not interpret response: %s, will choose first submission.", response
    )
