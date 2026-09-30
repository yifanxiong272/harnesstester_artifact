# file: sweagent/agent/reviewer.py:307-316
# asked: {"lines": [309, 310, 312, 313, 314], "branches": [[308, 312], [308, 313]]}
# gained: {"lines": [309, 310, 312, 313, 314], "branches": [[308, 312], [308, 313]]}

import pytest
from types import SimpleNamespace
from sweagent.agent.reviewer import Chooser


def make_chooser(max_len_submission: int, template: str) -> Chooser:
    """
    Create a Chooser instance without running __init__, and attach a minimal config
    that provides the attributes used by format_submission.
    """
    chooser = Chooser.__new__(Chooser)
    chooser.config = SimpleNamespace(max_len_submission=max_len_submission, submission_template=template)
    return chooser


def make_submission(info: dict, to_format: dict):
    """
    Create a minimal submission-like object with .info and .to_format_dict().
    """
    def to_format_dict():
        return to_format

    return SimpleNamespace(info=info, to_format_dict=to_format_dict)


def test_format_submission_returns_invalid_when_submission_missing():
    chooser = make_chooser(max_len_submission=10, template="Should not be used")
    # submission info has no "submission" key -> .get("submission") is None -> invalid
    submission = make_submission(info={}, to_format={})
    result = chooser.format_submission("problem", submission)
    assert result == "Solution invalid."


def test_format_submission_returns_invalid_when_submission_too_long():
    # max_len_submission > 0 and length of submission string > max_len_submission -> invalid
    chooser = make_chooser(max_len_submission=2, template="Should not be used")
    submission = make_submission(info={"submission": "too long"}, to_format={})
    result = chooser.format_submission("problem", submission)
    assert result == "Solution invalid."


def test_format_submission_renders_template_with_to_format_dict():
    # valid submission: not None and length <= max_len_submission -> template should render
    chooser = make_chooser(max_len_submission=100, template="Answer: {{value}}; ID: {{id}}")
    submission = make_submission(info={"submission": "ok"}, to_format={"value": 123, "id": "abc"})
    result = chooser.format_submission("problem statement", submission)
    assert result == "Answer: 123; ID: abc"
