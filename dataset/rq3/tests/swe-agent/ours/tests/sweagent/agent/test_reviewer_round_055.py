import types
import pytest

from sweagent.agent import reviewer as reviewer_mod

# Create lightweight stand-ins for model, reviewer, and config to avoid external dependencies
class DummyModel:
    def __init__(self):
        # minimal attribute referenced by ScoreRetryLoop during init
        self.stats = types.SimpleNamespace(instance_cost=0)

class SimpleReviewResult:
    def __init__(self, accept: float):
        self.accept = accept

class DummyReviewer:
    def __init__(self, return_value: SimpleReviewResult):
        self._rv = return_value
        self.called_with = None

    def review(self, instance, submission):
        # record call for deterministic assertions
        self.called_with = (instance, submission)
        return self._rv

class DummyReviewerConfig:
    def __init__(self, reviewer: DummyReviewer):
        self._reviewer = reviewer

    def get_reviewer(self, model):
        # preserve the expected signature used in ScoreRetryLoop.__init__
        return self._reviewer

class DummyConfig:
    def __init__(self, reviewer_config, model="dummy"):
        self.model = model
        self.reviewer_config = reviewer_config
        # provide defaults that make other ScoreRetryLoop methods benign if called
        self.accept_score = 0.5
        self.cost_limit = 0
        self.max_attempts = 0
        self.max_accepts = 0
        self.min_budget_for_new_attempt = 0

class SimpleSubmission:
    def __init__(self, info: dict):
        # ScoreRetryLoop._review accesses submission.info.get(...)
        self.info = info
        # include a minimal model_stats attribute so any other code that sums stats won't fail
        self.model_stats = types.SimpleNamespace(instance_cost=0)


def make_loop(monkeypatch, reviewer_return: SimpleReviewResult):
    """Helper to construct a ScoreRetryLoop with patched get_model and deterministic collaborators."""
    dummy_model = DummyModel()

    # Patch get_model in the reviewer module so __init__ doesn't call any external provider
    monkeypatch.setattr(reviewer_mod, "get_model", lambda *args, **kwargs: dummy_model)

    dummy_reviewer = DummyReviewer(reviewer_return)
    reviewer_cfg = DummyReviewerConfig(dummy_reviewer)
    cfg = DummyConfig(reviewer_cfg)

    # Construct the ScoreRetryLoop instance under test
    loop = reviewer_mod.ScoreRetryLoop(cfg, problem_statement=object())
    return loop, dummy_reviewer


def test_review_increments_on_exit_cost_round_055(monkeypatch):
    """When submission.info.exit_status contains 'exit_cost' (case-insensitive), _n_consec_exit_cost increments and review is recorded."""
    expected_accept = 0.42
    rv = SimpleReviewResult(expected_accept)
    loop, dummy_reviewer = make_loop(monkeypatch, rv)

    # initial value should be zero
    assert loop._n_consec_exit_cost == 0

    # Provide an exit_status containing 'EXIT_COST' in mixed case to test case-insensitive check
    submission = SimpleSubmission({"exit_status": "Some serious EXIT_COST occurred"})

    # on_submit triggers _review() internally
    loop.on_submit(submission)

    # The reviewer should have been called with the problem statement and our submission
    called_instance, called_submission = dummy_reviewer.called_with
    assert called_submission is submission

    # The review should have been appended and its accept value returned by the reviewer result
    assert loop.reviews[-1].accept == expected_accept

    # The consecutive exit cost counter should have incremented from 0 to 1
    assert loop._n_consec_exit_cost == 1


def test_review_resets_on_non_exit_cost_round_055(monkeypatch):
    """When submission.info.exit_status does not contain 'exit_cost', _n_consec_exit_cost is reset to 0 even if previously positive."""
    expected_accept = 0.9
    rv = SimpleReviewResult(expected_accept)
    loop, dummy_reviewer = make_loop(monkeypatch, rv)

    # Simulate prior consecutive exit-cost submissions
    loop._n_consec_exit_cost = 5

    # Provide an exit_status that does not contain the substring 'exit_cost'
    submission = SimpleSubmission({"exit_status": "Completed without extra cost"})

    loop.on_submit(submission)

    # The last review accept value should match what our reviewer returned
    assert loop.reviews[-1].accept == expected_accept

    # The consecutive exit cost counter should have been reset to zero
    assert loop._n_consec_exit_cost == 0
