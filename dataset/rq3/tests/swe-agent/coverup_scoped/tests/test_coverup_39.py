# file: sweagent/agent/reviewer.py:307-316
# asked: {"lines": [309, 310, 312, 313, 314], "branches": [[308, 312], [308, 313]]}
# gained: {"lines": [309, 310, 312, 313, 314], "branches": [[308, 312], [308, 313]]}

import pytest
from sweagent.agent.reviewer import Chooser


class SimpleConfig:
    def __init__(self, submission_template: str, max_len_submission: int):
        self.submission_template = submission_template
        self.max_len_submission = max_len_submission


class SimpleSubmission:
    def __init__(self, info: dict, format_dict: dict):
        self.info = info
        self._format_dict = format_dict

    def to_format_dict(self, *args, **kwargs):
        return self._format_dict


def test_format_submission_missing_submission():
    # Create Chooser instance without running __init__ to avoid heavy dependencies
    chooser = Chooser.__new__(Chooser)
    chooser.config = SimpleConfig(submission_template="{{ignored}}", max_len_submission=10)

    # Submission missing 'submission' key -> should be invalid
    sub = SimpleSubmission(info={}, format_dict={})
    result = chooser.format_submission("problem statement", sub)
    assert result == "Solution invalid."


def test_format_submission_too_long_submission():
    chooser = Chooser.__new__(Chooser)
    chooser.config = SimpleConfig(submission_template="{{ignored}}", max_len_submission=5)

    # 'submission' present but length > max_len_submission -> invalid
    long_text = "x" * 6
    sub = SimpleSubmission(info={"submission": long_text}, format_dict={})
    result = chooser.format_submission("problem statement", sub)
    assert result == "Solution invalid."


def test_format_submission_renders_template():
    chooser = Chooser.__new__(Chooser)
    chooser.config = SimpleConfig(submission_template="Hello {{name}}", max_len_submission=100)

    # Valid submission -> template should render using to_format_dict()
    sub = SimpleSubmission(info={"submission": "ok"}, format_dict={"name": "Alice"})
    result = chooser.format_submission("problem statement", sub)
    assert result.strip() == "Hello Alice"
