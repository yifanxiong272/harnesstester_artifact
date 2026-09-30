# file: sweagent/agent/reviewer.py:400-414
# asked: {"lines": [401, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414], "branches": [[404, 405], [404, 407], [408, 409], [408, 411], [411, 412], [411, 414]]}
# gained: {"lines": [401, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414], "branches": [[404, 405], [404, 407], [408, 409], [408, 411], [411, 412], [411, 414]]}

import pytest
from types import SimpleNamespace

from sweagent.agent.reviewer import Reviewer


def make_reviewer_with_score_range(score_min, score_max):
    # create instance without calling __init__ to avoid other dependencies
    reviewer = object.__new__(Reviewer)
    reviewer._config = SimpleNamespace(score_range=(score_min, score_max))
    return reviewer


def test_interpret_no_numbers_raises_value_error():
    reviewer = make_reviewer_with_score_range(0.0, 1.0)
    response = "Some analysis\nfinal verdict: nope"
    with pytest.raises(ValueError) as excinfo:
        reviewer.interpret(response)
    # last line is "final verdict: nope" and should be repr-ed in the message
    expected = "Could not interpret response: 'final verdict: nope'"
    assert str(excinfo.value) == expected


def test_interpret_number_below_min_raises_value_error():
    reviewer = make_reviewer_with_score_range(0.0, 10.0)
    # last line contains a single negative number which is below min 0.0
    response = "analysis...\n-1.2"
    with pytest.raises(ValueError) as excinfo:
        reviewer.interpret(response)
    assert str(excinfo.value) == "Score -1.2 is below the minimum score 0.0"


def test_interpret_number_above_max_raises_value_error():
    reviewer = make_reviewer_with_score_range(0.0, 1.0)
    # last line contains an integer 5 which is above max 1.0
    response = "blah\nresult: 5"
    with pytest.raises(ValueError) as excinfo:
        reviewer.interpret(response)
    assert str(excinfo.value) == "Score 5.0 is above the maximum score 1.0"


def test_interpret_returns_last_number_within_range():
    reviewer = make_reviewer_with_score_range(-10.0, 10.0)
    # last line has multiple numbers; the last one (3.1415) should be returned
    response = "ignored line\nvalues: 0 1 3.1415"
    result = reviewer.interpret(response)
    assert isinstance(result, float)
    assert result == 3.1415
