# file: sweagent/agent/reviewer.py:180-197
# asked: {"lines": [197], "branches": []}
# gained: {"lines": [197], "branches": []}

import pytest
import types

import sweagent.agent.reviewer as reviewer


def test_get_retry_loop_returns_instance(monkeypatch):
    class DummyChooserRetryLoop:
        def __init__(self, config, problem_statement):
            # store so we can assert later
            self._config = config
            self._problem_statement = problem_statement

    # Patch the real ChooserRetryLoop to avoid heavy initialization
    monkeypatch.setattr(reviewer, "ChooserRetryLoop", DummyChooserRetryLoop)

    # Construct the config without validation to avoid needing full ChooserConfig
    config = reviewer.ChooserRetryLoopConfig.construct(
        type="chooser",
        chooser=object(),
        max_attempts=3,
        min_budget_for_new_attempt=0.0,
        cost_limit=100.0,
    )

    ps = object()
    result = config.get_retry_loop(ps)

    assert isinstance(result, DummyChooserRetryLoop)
    assert result._config is config
    assert result._problem_statement is ps


def test_get_retry_loop_propagates_exception(monkeypatch):
    class RaisingChooserRetryLoop:
        def __init__(self, config, problem_statement):
            raise ValueError("init failed")

    monkeypatch.setattr(reviewer, "ChooserRetryLoop", RaisingChooserRetryLoop)

    config = reviewer.ChooserRetryLoopConfig.construct(
        type="chooser",
        chooser=object(),
        max_attempts=1,
        min_budget_for_new_attempt=0.0,
        cost_limit=10.0,
    )

    with pytest.raises(ValueError, match="init failed"):
        config.get_retry_loop(object())
