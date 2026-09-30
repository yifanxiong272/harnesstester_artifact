# file: sweagent/agent/models.py:744-786
# asked: {"lines": [748, 749, 750, 751, 753, 754, 755, 756, 786], "branches": [[749, 750], [749, 753], [784, 786]]}
# gained: {"lines": [748, 749, 750, 751, 753, 754, 755, 756, 786], "branches": [[749, 750], [784, 786]]}

import time
from types import SimpleNamespace
import pytest

from sweagent.agent.models import LiteLLMModel


class DummyLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg: str):
        self.warnings.append(msg)


def make_model_with_query_behavior(raise_once: bool = True):
    """
    Create a LiteLLMModel instance without calling __init__ and attach:
    - config with retry settings
    - logger that captures warnings
    - _history_to_messages that returns a simple message list
    - _query that either raises on first call then succeeds, or always succeeds
    """
    model = object.__new__(LiteLLMModel)

    # minimal config shape used by query()
    model.config = SimpleNamespace(
        retry=SimpleNamespace(retries=3, min_wait=0, max_wait=0)
    )

    model.logger = DummyLogger()

    model._history_to_messages = lambda history: [{"role": "user", "content": "hello"}]

    calls = {"n": 0}

    def _query(messages, n=None, temperature=None):
        calls["n"] += 1
        if raise_once and calls["n"] == 1:
            # any exception not in the retry-exclusion list; ValueError will be retried
            raise ValueError("transient")
        # return list of dicts; length equals n if n provided and >1
        if n is None or n == 1:
            return [{"content": "ok"}]
        return [{"content": f"ok_{i}"} for i in range(n)]

    model._query = _query
    return model


def test_query_triggers_retry_warning_and_returns_single(monkeypatch):
    """
    This test ensures:
    - the before_sleep retry warning path is executed (which reads attempt.retry_state.outcome and exception)
    - the function ultimately returns the single dict when n==1
    - the logger received a warning that includes the exception info
    """
    # prevent actual sleeping between retries
    monkeypatch.setattr(time, "sleep", lambda s: None)

    model = make_model_with_query_behavior(raise_once=True)

    result = model.query(history=[], n=1, temperature=None)

    # result should be the single dict (result[0] returned)
    assert isinstance(result, dict)
    assert result["content"] == "ok"

    # A warning should have been logged and should contain the exception name
    assert len(model.logger.warnings) >= 1
    # find any warning that mentions ValueError
    assert any("ValueError" in w for w in model.logger.warnings)
    # also check the warning has "slept for" formatting (from f-string)
    assert any("slept for" in w for w in model.logger.warnings)


def test_query_returns_list_when_n_greater_than_one(monkeypatch):
    """
    This test ensures that when n != 1 the final 'return result' branch is executed.
    No retry is needed here; _query will succeed immediately.
    """
    # prevent sleeping (even though no retry expected)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    model = make_model_with_query_behavior(raise_once=False)

    result = model.query(history=[], n=3, temperature=None)

    # Expect a list of length 3
    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0]["content"] == "ok_0"
    assert result[1]["content"] == "ok_1"
    assert result[2]["content"] == "ok_2"

    # No warnings should have been logged because no retry happened
    assert model.logger.warnings == []
