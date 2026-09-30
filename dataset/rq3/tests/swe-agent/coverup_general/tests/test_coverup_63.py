# file: sweagent/agent/reviewer.py:607-615
# asked: {"lines": [608, 609, 610, 611, 612, 614, 615], "branches": [[611, 612], [611, 614]]}
# gained: {"lines": [608, 609, 610, 611, 612, 614, 615], "branches": [[611, 612], [611, 614]]}

import types
import pytest
from types import SimpleNamespace
from sweagent.agent import reviewer as reviewer_mod
from sweagent.agent.reviewer import ScoreRetryLoop


class DummyReview:
    def __init__(self, accept):
        self.accept = accept


class DummyReviewer:
    def __init__(self, to_return):
        # to_return can be a DummyReview or a callable producing one
        self.to_return = to_return
        self.calls = []

    def review(self, problem_statement, submission):
        # record the call for assertions and return the configured result
        self.calls.append((problem_statement, submission))
        if callable(self.to_return):
            return self.to_return()
        return self.to_return


class DummySubmission:
    def __init__(self, info):
        # mimic the .info mapping used in _review
        self.info = dict(info)


def make_instance():
    # Create ScoreRetryLoop instance without running __init__, then set attributes required by _review
    inst = object.__new__(ScoreRetryLoop)
    # required attributes used in _review:
    # - _reviewer with .review(...)
    # - _problem_statement (can be any object)
    # - _submissions: list with at least one submission
    # - _reviews: list to be appended to
    # - _n_consec_exit_cost: int
    inst._problem_statement = SimpleNamespace()  # placeholder
    inst._reviewer = None
    inst._submissions = []
    inst._reviews = []
    inst._n_consec_exit_cost = 0
    return inst


def test_review_increments_exit_cost_when_exit_cost_in_status():
    inst = make_instance()

    # start with a non-zero consecutive count to verify increment
    inst._n_consec_exit_cost = 2

    # prepare a submission whose info contains exit_status with the substring exit_cost (mixed case)
    sub = DummySubmission({"exit_status": "Some Error: Exit_CoSt occurred"})
    inst._submissions.append(sub)

    # prepare a reviewer that returns a DummyReview with accept True
    review_obj = DummyReview(accept=True)
    dummy_reviewer = DummyReviewer(review_obj)
    inst._reviewer = dummy_reviewer

    # call the protected method
    result = inst._review()

    # assert return value equals review.accept
    assert result is True

    # the review object should have been appended to _reviews
    assert inst._reviews and inst._reviews[-1] is review_obj

    # consecutive exit cost counter should have incremented by 1
    assert inst._n_consec_exit_cost == 3

    # reviewer.review should have been called with the problem statement and the submission
    assert dummy_reviewer.calls == [(inst._problem_statement, sub)]


def test_review_resets_exit_cost_when_no_exit_cost_in_status():
    inst = make_instance()

    # start with a non-zero consecutive count to verify reset to 0
    inst._n_consec_exit_cost = 5

    # prepare a submission whose info either lacks exit_status or has one without the substring
    sub = DummySubmission({"exit_status": "some other message without the keyword"})
    inst._submissions.append(sub)

    # prepare a reviewer that returns a DummyReview with accept False
    review_obj = DummyReview(accept=False)
    dummy_reviewer = DummyReviewer(review_obj)
    inst._reviewer = dummy_reviewer

    # call the protected method
    result = inst._review()

    # assert return value equals review.accept
    assert result is False

    # the review object should have been appended to _reviews
    assert inst._reviews and inst._reviews[-1] is review_obj

    # consecutive exit cost counter should have been reset to 0
    assert inst._n_consec_exit_cost == 0

    # reviewer.review should have been called with the problem statement and the submission
    assert dummy_reviewer.calls == [(inst._problem_statement, sub)]
