import pytest
from sweagent.agent.reviewer import ScoreRetryLoop


class DummyReview:
    def __init__(self, accept):
        self.accept = accept


class DummyReviewer:
    def __init__(self, review_obj):
        self._review_obj = review_obj

    def review(self, problem_statement, submission):
        # Return the prepared review object deterministically
        return self._review_obj


class FakeSubmission:
    def __init__(self, info):
        self.info = info


def test_review_increments_exit_cost_round_057():
    """When exit_status contains 'exit_cost' (case-insensitive),
    _n_consec_exit_cost should be incremented and review.accept returned.
    """
    rev_obj = DummyReview(0.123)
    reviewer = DummyReviewer(rev_obj)

    # Instantiate without running __init__ to avoid unrelated setup
    sr = object.__new__(ScoreRetryLoop)
    sr._reviewer = reviewer
    sr._problem_statement = object()
    # last submission has an exit_status that includes 'exit_cost' (mixed case)
    sr._submissions = [FakeSubmission({"exit_status": "Error: Exit_Cost occurred"})]
    sr._reviews = []
    sr._n_consec_exit_cost = 2

    result = sr._review()

    # Observable behavior: returned accept value, appended review, incremented counter
    assert result == 0.123
    assert sr._reviews[-1] is rev_obj
    assert sr._n_consec_exit_cost == 3


def test_review_resets_exit_cost_round_057():
    """When exit_status is present but does NOT contain 'exit_cost',
    _n_consec_exit_cost should be reset to 0 and review.accept returned.
    """
    rev_obj = DummyReview(1.0)
    reviewer = DummyReviewer(rev_obj)

    sr = object.__new__(ScoreRetryLoop)
    sr._reviewer = reviewer
    sr._problem_statement = object()
    # last submission has an exit_status that does not include 'exit_cost'
    sr._submissions = [FakeSubmission({"exit_status": "completed normally"})]
    sr._reviews = []
    sr._n_consec_exit_cost = 7

    result = sr._review()

    # Observable behavior: returned accept value, appended review, counter reset
    assert result == 1.0
    assert sr._reviews[-1] is rev_obj
    assert sr._n_consec_exit_cost == 0
