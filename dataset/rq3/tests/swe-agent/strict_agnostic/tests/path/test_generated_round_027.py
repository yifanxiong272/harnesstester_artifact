import pytest

from sweagent.agent.reviewer import Reviewer


class _FakeConfig:
    def __init__(self, score_range):
        # score_range is expected to be a tuple (min, max)
        self.score_range = score_range


class _FakeSelf:
    def __init__(self, score_range):
        self._config = _FakeConfig(score_range)


def _call_interpret(fake_self, response: str):
    # Call the unbound function defined on Reviewer with a fake self
    # This avoids having to construct a full Reviewer instance.
    return Reviewer.interpret(fake_self, response)


def test_no_numbers_round_027():
    """
    When the last line contains no numeric token, interpret should raise a ValueError
    with an exact message containing the repr() of the last line.
    """
    fake = _FakeSelf((None, None))
    response = "Some lines\nNo digits here\n"

    with pytest.raises(ValueError) as excinfo:
        _call_interpret(fake, response)

    # The implementation uses last_line!r in the error message
    assert str(excinfo.value) == "Could not interpret response: 'No digits here'"


def test_below_minimum_round_027():
    """
    If a numeric value is parsed but is less than the configured minimum,
    interpret must raise a ValueError with the expected message including the
    numeric value and the minimum bound.
    """
    # Configure a minimum of 0.0 so a negative parsed number is below minimum
    fake = _FakeSelf((0.0, 1.0))
    response = "stuff\nfinal score: -1.2"

    with pytest.raises(ValueError) as excinfo:
        _call_interpret(fake, response)

    assert str(excinfo.value) == "Score -1.2 is below the minimum score 0.0"


def test_above_maximum_round_027():
    """
    If a numeric value is parsed but is greater than the configured maximum,
    interpret must raise a ValueError with the expected message including the
    numeric value and the maximum bound.
    """
    fake = _FakeSelf((0.0, 1.0))
    response = "info\nscore = 2"

    with pytest.raises(ValueError) as excinfo:
        _call_interpret(fake, response)

    # The parsed float will be formatted by Python float -> str as '2.0'
    assert str(excinfo.value) == "Score 2.0 is above the maximum score 1.0"


def test_within_range_round_027():
    """
    If a numeric value is parsed and it falls within [min, max], interpret should
    return the parsed float value.
    """
    fake = _FakeSelf((0.0, 5.0))
    response = "blah\nResult: 3.14\n"

    result = _call_interpret(fake, response)

    assert isinstance(result, float)
    # Exact numeric parity: parser should return 3.14
    assert result == 3.14
