from sweagent.agent import reviewer as reviewer_mod


def test_probe_001_tiebreak_prefers_numeric_zero_api_calls():
    """
    Activation: construct a ScoreRetryLoop instance with two tied top accept scores.
    One submission has model_stats.api_calls == 0 and the other has 5.

    Invariant: numeric zero (0) is a valid count and should be treated as smaller than 5.
    The test asserts that get_best() selects the submission with api_calls == 0 (index 0).
    """

    # Local helpers (kept local to avoid polluting top-level symbols)
    class _DR:
        def __init__(self, accept: float):
            self.accept = accept

    class _ModelStats:
        def __init__(self, api_calls: int | None):
            # Only api_calls is needed by get_best
            self.api_calls = api_calls

    class _Submission:
        def __init__(self, api_calls: int | None):
            self.model_stats = _ModelStats(api_calls)
            # code elsewhere may inspect .info; provide an empty dict to be safe
            self.info = {}

    class _Logger:
        def debug(self, *a, **k):
            return None

        def info(self, *a, **k):
            return None

    def _make_instance(reviews_accepts, api_calls_list):
        cls = reviewer_mod.ScoreRetryLoop
        inst = cls.__new__(cls)
        # Assign the minimal attributes used by get_best
        inst._reviews = [_DR(a) for a in reviews_accepts]
        inst._submissions = [_Submission(ac) for ac in api_calls_list]
        inst.logger = _Logger()
        return inst

    # Construct the tied-top scenario: two reviews with identical accept values
    inst = _make_instance([1.0, 1.0], [0, 5])

    chosen = inst.get_best()

    # Primary observable assertion: numeric zero should be preferred (index 0)
    assert chosen == 0, (
        f"Expected the submission with api_calls==0 (index 0) to be selected, got {chosen}. "
        "This reveals handling where 0 may be treated as falsy and replaced by +inf in the tie-break key."
    )
