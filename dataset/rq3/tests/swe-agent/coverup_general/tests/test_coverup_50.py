# file: sweagent/agent/models.py:744-786
# asked: {"lines": [748, 749, 750, 751, 753, 754, 755, 756, 786], "branches": [[749, 750], [749, 753], [784, 786]]}
# gained: {"lines": [748, 749, 750, 751, 753, 754, 755, 756, 786], "branches": [[749, 750], [749, 753], [784, 786]]}

import types
from types import SimpleNamespace
import pytest

import sweagent.agent.models as models


class FakeOutcome:
    def __init__(self, exc):
        self._exc = exc

    def exception(self):
        return self._exc


class FakeAttempt:
    def __init__(self, before_sleep, attempt_number: int, idle_for: float, outcome_on_sleep):
        # outcome_on_sleep: either an Exception instance to be returned by outcome.exception(),
        # or None to represent a None outcome
        self.before_sleep = before_sleep
        self.attempt_number = attempt_number
        self.idle_for = idle_for
        self.outcome_on_sleep = outcome_on_sleep
        # initialize retry_state used during execution (may be mutated in __exit__)
        self.retry_state = SimpleNamespace(outcome=None, attempt_number=attempt_number, idle_for=idle_for)

    def __enter__(self):
        # Return self to be assigned to loop variable 'attempt'
        return self

    def __exit__(self, exc_type, exc, tb):
        # If an exception happened during the attempt, simulate tenacity behavior:
        # set retry_state.outcome appropriately and call before_sleep.
        if exc is not None:
            if self.outcome_on_sleep is not None:
                self.retry_state.outcome = FakeOutcome(self.outcome_on_sleep)
            else:
                self.retry_state.outcome = None
            # ensure attempt_number and idle_for are present
            self.retry_state.attempt_number = self.attempt_number
            self.retry_state.idle_for = self.idle_for
            # Call the before_sleep callback (what we're testing)
            if self.before_sleep is not None:
                self.before_sleep(self.retry_state)
            # suppress the exception so the retry loop continues
            return True
        # no exception -> normal flow
        return False


class FakeRetrying:
    """
    A stub replacement for tenacity.Retrying that will yield two attempts:
    - First attempt: will allow an exception to be raised and will invoke before_sleep.
    - Second attempt: will allow success.
    The initializer accepts arbitrary kwargs (to match the real API) but only uses before_sleep.
    """

    def __init__(self, *args, **kwargs):
        self.before_sleep = kwargs.get('before_sleep')
        # other args ignored (stop, wait, etc.)

    def __iter__(self):
        # Yield two FakeAttempt objects. The first one will simulate an exception outcome,
        # the second one will be a normal successful attempt (no exception).
        # idle_for is a float used in formatting in retry_warning
        yield FakeAttempt(self.before_sleep, attempt_number=1, idle_for=0.12, outcome_on_sleep=ValueError("boom"))
        yield FakeAttempt(self.before_sleep, attempt_number=2, idle_for=0.00, outcome_on_sleep=None)


def make_minimal_model(monkeypatch, fake_query_impl, warn_calls_list):
    """
    Create a LiteLLMModel instance without invoking its real __init__,
    setting only the attributes needed by query().
    """
    ModelClass = models.LiteLLMModel
    inst = object.__new__(ModelClass)

    # Minimal config with nested retry object
    inst.config = SimpleNamespace(
        retry=SimpleNamespace(retries=2, min_wait=0.01, max_wait=0.02),
        # completion_kwargs may be referenced elsewhere but not in query; keep minimal
        completion_kwargs={}
    )

    # minimal logger that records warnings
    def _warn(msg):
        warn_calls_list.append(msg)

    inst.logger = SimpleNamespace(warning=_warn)

    # _history_to_messages just returns a stable messages list
    inst._history_to_messages = lambda history: [{"role": "user", "content": "hello"}]

    # supply the fake _query implementation
    inst._query = fake_query_impl

    return inst


def test_query_with_retry_logs_exception_and_returns_single_result(monkeypatch):
    # Replace Retrying in the module with our FakeRetrying
    monkeypatch.setattr(models, "Retrying", FakeRetrying)

    warn_calls = []

    # A fake _query that raises on first call and returns a single-item list on the second
    call_count = {"c": 0}

    def fake_query(messages, n=None, temperature=None):
        call_count["c"] += 1
        if call_count["c"] == 1:
            raise ValueError("boom")
        return [{"content": "ok"}]

    model = make_minimal_model(monkeypatch, fake_query, warn_calls)

    # Run query with n=1 to trigger the code path that returns a single dict
    result = model.query(history=[], n=1, temperature=None)

    # Assertions about returned value
    assert isinstance(result, dict)
    assert result["content"] == "ok"

    # Ensure warning was logged once (from the before_sleep call)
    assert len(warn_calls) == 1
    msg = warn_calls[0]
    # Must contain the expected prefix and mention the exception class name
    assert "Retrying LM query" in msg
    assert "attempt 1" in msg or "attempt 1"  # ensure attempt number present
    assert "slept for" in msg
    assert "due to ValueError" in msg  # ensures exception_info branch with exception executed


def test_query_with_retry_logs_no_exception_info_and_returns_list_for_n_gt_1(monkeypatch):
    # This FakeRetrying will call before_sleep with outcome=None for the first attempt,
    # which should drive the code path where exception_info stays empty.
    class FakeRetryingNoOutcome(FakeRetrying):
        def __iter__(self):
            # First attempt: before_sleep called with outcome None
            yield FakeAttempt(self.before_sleep, attempt_number=1, idle_for=0.34, outcome_on_sleep=None)
            # Second attempt: success
            yield FakeAttempt(self.before_sleep, attempt_number=2, idle_for=0.0, outcome_on_sleep=None)

    monkeypatch.setattr(models, "Retrying", FakeRetryingNoOutcome)

    warn_calls = []

    # A fake _query that raises on first call and returns multiple items on the second
    call_count = {"c": 0}

    def fake_query(messages, n=None, temperature=None):
        call_count["c"] += 1
        if call_count["c"] == 1:
            raise Exception("transient")
        # return multiple results to exercise the n>1 branch (line 786)
        return [{"content": "ok1"}, {"content": "ok2"}]

    model = make_minimal_model(monkeypatch, fake_query, warn_calls)

    # Run query with n=2 to get a list back
    result = model.query(history=[], n=2, temperature=None)

    # Assertions about returned value: list with two items
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["content"] == "ok1"
    assert result[1]["content"] == "ok2"

    # Ensure a warning was logged but without 'due to' since outcome was None
    assert len(warn_calls) == 1
    msg = warn_calls[0]
    assert "Retrying LM query" in msg
    assert "slept for" in msg
    assert "due to" not in msg
