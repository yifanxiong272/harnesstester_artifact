from sweagent.agent.reviewer import ScoreRetryLoop

class _FakeLogger:
    def debug(self, *a, **k):
        return None
    def info(self, *a, **k):
        return None

class _FakeReview:
    def __init__(self, accept):
        self.accept = accept

class _FakeModelStats:
    def __init__(self, api_calls):
        self.api_calls = api_calls

class _FakeSubmission:
    def __init__(self, api_calls):
        self.model_stats = _FakeModelStats(api_calls)

def test_probe_001_tie_break_prefers_smallest_finite_api_calls():
    loop = object.__new__(ScoreRetryLoop)
    loop.logger = _FakeLogger()

    tied_score = 1.0
    loop._reviews = [_FakeReview(tied_score), _FakeReview(tied_score)]
    loop._submissions = [_FakeSubmission(10), _FakeSubmission(0)]

    chosen = loop.get_best()
    assert chosen == 1, (
        f"Expected get_best() to choose the submission with api_calls==0 (index 1), "
        f"but got {chosen}. This reveals whether falsy 0 is incorrectly treated as missing/infinite."
    )
