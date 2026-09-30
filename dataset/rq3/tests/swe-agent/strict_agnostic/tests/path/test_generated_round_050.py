import logging
import pytest
from sweagent.agent.action_sampler import BinaryTrajectoryComparison


def _make_sampler():
    """Create a BinaryTrajectoryComparison instance without running full __init__.
    interpret only needs self._logger, so we attach a simple logger.
    """
    inst = object.__new__(BinaryTrajectoryComparison)
    inst._logger = logging.getLogger("sweagent.test")
    return inst


def test_interpret_first_round_050():
    sampler = _make_sampler()
    # last line contains the word 'first' (case-insensitive) -> should return 0
    response = "Some context\nThe model chose the First submission"
    assert sampler.interpret(response) == 0


def test_interpret_second_round_050():
    sampler = _make_sampler()
    # last line contains the word 'second' (case-insensitive) -> should return 1
    response = "Header info\nI think the SECOND one is better"
    assert sampler.interpret(response) == 1


def test_interpret_unparsable_round_050(caplog):
    sampler = _make_sampler()
    # last line contains neither 'first' nor 'second' -> should log a warning and return 0
    response = "leading text\nNeither choice is clear here"
    with caplog.at_level(logging.WARNING):
        result = sampler.interpret(response)
    assert result == 0
    # assert that a warning mentioning inability to interpret was emitted
    assert any("Could not interpret response" in rec.getMessage() for rec in caplog.records)
