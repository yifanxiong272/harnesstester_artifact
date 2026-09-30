import types
import pytest
from types import SimpleNamespace
import sweagent.agent.reviewer as reviewer_mod


def _make_self(min_score, max_score):
    # Create a lightweight fake 'self' with the exact attribute used by interpret
    cfg = SimpleNamespace(score_range=(min_score, max_score))
    return SimpleNamespace(_config=cfg)


def test_interpret_no_numbers_round_025():
    """When the last line contains no numbers, interpret should raise ValueError
    with a message that includes the repr of the last line.
    """
    self_obj = _make_self(None, None)
    response = "some preliminary 123\nno numbers here  "  # last line has no numbers

    with pytest.raises(ValueError) as excinfo:
        reviewer_mod.Reviewer.interpret(self_obj, response)

    last_line = response.strip().split("\n")[-1].strip()
    expected = f"Could not interpret response: {last_line!r}"
    assert str(excinfo.value) == expected


def test_interpret_below_min_round_025():
    """When the extracted number is below the configured minimum, a ValueError
    naming the score and the minimum is raised.
    """
    self_obj = _make_self(0.0, None)  # minimum is 0.0
    response = "ignored\n-1.5"  # last line contains -1.5

    with pytest.raises(ValueError) as excinfo:
        reviewer_mod.Reviewer.interpret(self_obj, response)

    assert str(excinfo.value) == "Score -1.5 is below the minimum score 0.0"


def test_interpret_above_max_round_025():
    """When the extracted number is above the configured maximum, a ValueError
    naming the score and the maximum is raised.
    """
    self_obj = _make_self(None, 3.0)  # maximum is 3.0
    response = "meta\n5"  # last line contains 5

    with pytest.raises(ValueError) as excinfo:
        reviewer_mod.Reviewer.interpret(self_obj, response)

    assert str(excinfo.value) == "Score 5.0 is above the maximum score 3.0"


def test_interpret_within_range_round_025():
    """When the extracted number is within the configured [min,max], the
    float value is returned unchanged.
    """
    self_obj = _make_self(0.0, 1.0)
    response = "whatever\n0.75"

    result = reviewer_mod.Reviewer.interpret(self_obj, response)
    assert isinstance(result, float)
    assert result == 0.75


def test_interpret_uses_last_number_round_025():
    """If multiple numbers appear on the last line, the last one is chosen.
    This ensures the regex + indexing behavior is covered.
    """
    self_obj = _make_self(None, None)
    response = "123\nnumbers 10 20"

    result = reviewer_mod.Reviewer.interpret(self_obj, response)
    assert result == 20.0
