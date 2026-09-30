import pytest

import sweagent.agent.reviewer as reviewer


def test_get_retry_loop_returns_chooser_retry_loop_round_137():
    """Verify that ChooserRetryLoopConfig.get_retry_loop constructs and returns
    the ChooserRetryLoop using the same config object and the supplied
    problem_statement. We monkeypatch reviewer.ChooserRetryLoop to a fake
    class that records constructor arguments. Unlike the previous failing
    attempt, we now construct a real ChooserRetryLoopConfig via its
    constructor so pydantic internals are properly initialized.
    """
    created = {}

    class FakeChooserRetryLoop:
        def __init__(self, config, problem_statement):
            created['config'] = config
            created['problem_statement'] = problem_statement

        def __repr__(self):
            return "<FakeChooserRetryLoop>"

    original = reviewer.ChooserRetryLoop
    reviewer.ChooserRetryLoop = FakeChooserRetryLoop

    try:
        # Build a minimal chooser config as a dict; pydantic will coerce nested models.
        chooser_dict = {
            "model": {},
            "system_template": "sys",
            "instance_template": "inst",
            "submission_template": "sub",
        }

        cfg = reviewer.ChooserRetryLoopConfig(
            chooser=chooser_dict,
            max_attempts=1,
            cost_limit=10.0,
        )

        sentinel_problem = object()

        result = cfg.get_retry_loop(sentinel_problem)

        assert isinstance(result, FakeChooserRetryLoop)
        assert created['config'] is cfg
        assert created['problem_statement'] is sentinel_problem

    finally:
        reviewer.ChooserRetryLoop = original
