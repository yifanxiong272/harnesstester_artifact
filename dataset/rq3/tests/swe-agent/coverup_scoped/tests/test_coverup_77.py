# file: sweagent/agent/reviewer.py:521-522
# asked: {"lines": [522], "branches": []}
# gained: {"lines": [522], "branches": []}

import pytest
from sweagent.agent.reviewer import ChooserRetryLoop


def _make_chooser_retry_loop_without_init():
    # Create an instance without calling __init__ to avoid heavy dependencies.
    loop = object.__new__(ChooserRetryLoop)
    loop._submissions = []
    return loop


def test_on_submit_appends_single_submission():
    loop = _make_chooser_retry_loop_without_init()
    submission = object()
    loop.on_submit(submission)
    assert isinstance(loop._submissions, list)
    assert loop._submissions == [submission]
    # ensure same object reference was stored
    assert loop._submissions[0] is submission


def test_on_submit_appends_multiple_and_preserves_reference_and_order():
    loop = _make_chooser_retry_loop_without_init()

    class Dummy:
        pass

    a = Dummy()
    b = Dummy()

    loop.on_submit(a)
    loop.on_submit(b)

    assert loop._submissions == [a, b]
    # mutate original and verify stored reference sees mutation
    a.some_field = "changed"
    assert getattr(loop._submissions[0], "some_field") == "changed"
