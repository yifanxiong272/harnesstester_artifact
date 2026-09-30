# file: sweagent/agent/reviewer.py:607-615
# asked: {"lines": [608, 609, 610, 611, 612, 614, 615], "branches": [[611, 612], [611, 614]]}
# gained: {"lines": [608, 609, 610, 611, 612, 614, 615], "branches": [[611, 612], [611, 614]]}

import types
import pytest

from sweagent.agent.reviewer import ScoreRetryLoop


class DummyReview:
    def __init__(self, accept):
        self.accept = accept


class DummyReviewer:
    def __init__(self, result):
        self.result = result
        self.called_with = None

    def review(self, problem_statement, submission):
        # record for assertions
        self.called_with = (problem_statement, submission)
        return self.result


class DummySubmission:
    def __init__(self, info):
        self.info = info


def make_instance():
    # Create instance without calling __init__ to avoid heavy dependencies.
    inst = object.__new__(ScoreRetryLoop)
    # Provide minimal required attributes used by _review
    inst._problem_statement = "dummy-problem"
    inst._reviews = []
    inst._submissions = []
    inst._n_consec_exit_cost = 0
    return inst


def test_review_increments_exit_cost_and_appends_review():
    inst = make_instance()
    # reviewer returns a DummyReview with accept value (float)
    review_result = DummyReview(accept=0.75)
    reviewer = DummyReviewer(review_result)
    inst._reviewer = reviewer

    # submission with exit_status containing 'exit_cost' (case-insensitive)
    submission = DummySubmission(info={"exit_status": "Some EXIT_COST occurred"})
    inst._submissions.append(submission)

    # Ensure initial counter is zero
    inst._n_consec_exit_cost = 0

    returned = inst._review()

    # The reviewer should have been called with the problem statement and submission
    assert reviewer.called_with == (inst._problem_statement, submission)
    # The review object should be appended to _reviews
    assert inst._reviews and inst._reviews[-1] is review_result
    # The counter should have incremented by 1
    assert inst._n_consec_exit_cost == 1
    # The returned value should be the review.accept value
    assert returned == pytest.approx(0.75)


def test_review_resets_exit_cost_when_no_exit_status():
    inst = make_instance()
    review_result = DummyReview(accept=0.0)
    reviewer = DummyReviewer(review_result)
    inst._reviewer = reviewer

    # submission with no exit_status key
    submission = DummySubmission(info={})
    inst._submissions.append(submission)

    # Set counter to non-zero to verify it gets reset
    inst._n_consec_exit_cost = 5

    returned = inst._review()

    # Review appended
    assert inst._reviews and inst._reviews[-1] is review_result
    # Counter should be reset to 0
    assert inst._n_consec_exit_cost == 0
    # Return value equals review.accept
    assert returned == pytest.approx(0.0)
