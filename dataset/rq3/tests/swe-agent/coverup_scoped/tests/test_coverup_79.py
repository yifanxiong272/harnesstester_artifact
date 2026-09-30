# file: sweagent/agent/reviewer.py:589-591
# asked: {"lines": [591], "branches": []}
# gained: {"lines": [591], "branches": []}

import pytest
from sweagent.agent.reviewer import ScoreRetryLoop


def test_n_attempts_with_empty_submissions():
    # Create instance without calling __init__ to avoid heavy initialization
    loop = object.__new__(ScoreRetryLoop)
    # ensure attribute exists and is empty
    loop._submissions = []
    assert isinstance(loop._submissions, list)
    assert loop._n_attempts == 0


def test_n_attempts_with_multiple_submissions():
    loop = object.__new__(ScoreRetryLoop)
    # populate with dummy submissions; values don't matter, only length does
    loop._submissions = ["s1", "s2", "s3", None]
    assert loop._n_attempts == 4
    # verify that property reflects changes to the underlying list
    loop._submissions.append("s5")
    assert loop._n_attempts == 5
