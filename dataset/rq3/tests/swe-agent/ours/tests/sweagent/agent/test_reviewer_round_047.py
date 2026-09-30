from sweagent.agent.reviewer import ScoreRetryLoop


class DummyLogger:
    def __init__(self):
        self.debug_msgs = []
        self.info_msgs = []

    def debug(self, msg):
        # capture debug messages for assertions
        self.debug_msgs.append(str(msg))

    def info(self, msg):
        # capture info messages for assertions
        self.info_msgs.append(str(msg))


class DummyModelStats:
    def __init__(self, api_calls):
        # mirror the attribute name used by the production code
        self.api_calls = api_calls


class DummySubmission:
    def __init__(self, api_calls):
        self.model_stats = DummyModelStats(api_calls)


class DummyReview:
    def __init__(self, accept):
        # the production code accesses .accept
        self.accept = accept


def test_get_best_empty_reviews_round_047():
    """When there are no reviews, get_best should return None and not emit scores logging."""
    inst = ScoreRetryLoop.__new__(ScoreRetryLoop)
    # simulate internal state directly to avoid dependence on constructor
    inst._reviews = []
    inst._submissions = []
    inst.logger = DummyLogger()

    result = inst.get_best()

    assert result is None
    # When there are no reviews the code returns early so no debug/info should be emitted
    assert inst.logger.debug_msgs == []
    assert inst.logger.info_msgs == []


def test_get_best_tie_breaker_round_047():
    """When multiple reviews share the max score, choose the submission with the fewest api_calls.

    This test constructs three reviews with scores [0.8, 0.8, 0.7]. The two top-scoring
    submissions have api_calls values None and 5; None should be treated as infinity so
    the submission with 5 api_calls (index 1) should be chosen.
    """
    inst = ScoreRetryLoop.__new__(ScoreRetryLoop)

    # two reviews tie for best score (0.8), third is lower
    inst._reviews = [DummyReview(0.8), DummyReview(0.8), DummyReview(0.7)]

    # corresponding submissions: first has None api_calls (treated as inf), second has 5, third has 2
    inst._submissions = [DummySubmission(None), DummySubmission(5), DummySubmission(2)]

    inst.logger = DummyLogger()

    chosen = inst.get_best()

    # Expect index 1 because submission at index 1 has 5 api_calls which is less than inf
    assert chosen == 1

    # The code logs scores (debug) and info about the chosen submission
    assert any(msg.startswith("Scores:") for msg in inst.logger.debug_msgs), (
        "Expected a debug message that starts with 'Scores:'"
    )
    assert inst.logger.info_msgs == [f"Best submission: {chosen}"]
