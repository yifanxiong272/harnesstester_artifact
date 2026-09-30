import types
from types import SimpleNamespace
import pytest

import sweagent.agent.models as models


class _OutcomeWithException:
    def __init__(self, exc):
        self._exc = exc

    def exception(self):
        return self._exc


class FakeAttempt:
    def __init__(self, retry_state, before_sleep):
        self.retry_state = retry_state
        # before_sleep is the callback passed into Retrying in the real code
        self._before_sleep = before_sleep

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Simulate tenacity calling the before_sleep callback after an attempt
        if self._before_sleep is not None:
            # Call with the retry_state object to match the real callback signature
            try:
                self._before_sleep(self.retry_state)
            except Exception:
                # Ensure deterministic behavior in tests; swallow any unexpected errors
                pass
        return False


class FakeRetrying:
    def __init__(self, *args, before_sleep=None, **kwargs):
        # Store the before_sleep callback so FakeAttempt can call it
        self._before_sleep = before_sleep

    def __iter__(self):
        # Use a per-test configured retry state placed on the module under test
        state = getattr(models, "_TEST_RETRY_STATE", None)
        # Yield a single FakeAttempt to exercise the loop and the before_sleep callback
        attempt = FakeAttempt(state, self._before_sleep)
        yield attempt


def _make_retry_state(outcome_obj, attempt_number, idle_for):
    return SimpleNamespace(outcome=outcome_obj, attempt_number=attempt_number, idle_for=idle_for)


def _make_fake_self(return_value, logged_list):
    """Create a minimal 'self' with the attributes LiteLLMModel.query expects.

    - _history_to_messages(history) -> list (not used beyond being passed through)
    - config.retry.* values (used only to construct the Retrying call; our FakeRetrying ignores them)
    - logger.warning(msg) that appends to logged_list so tests can assert on the message
    - _query(messages, n=None, temperature=None) -> return_value
    """
    fake = SimpleNamespace()
    fake._history_to_messages = lambda history: ["dummy-message"]
    fake.config = SimpleNamespace(retry=SimpleNamespace(retries=1, min_wait=0.1, max_wait=0.2))

    class _Logger:
        def __init__(self, target_list):
            self._list = target_list

        def warning(self, msg):
            # Keep deterministic formatting as produced by the code under test
            self._list.append(msg)

    fake.logger = _Logger(logged_list)

    def _query(messages, n=None, temperature=None):
        return return_value

    fake._query = _query
    return fake


def test_retry_warning_with_exception_round_054(monkeypatch):
    # Arrange: produce a retry_state whose outcome.exception() returns a real Exception
    exc = Exception("boom")
    outcome = _OutcomeWithException(exc)
    models._TEST_RETRY_STATE = _make_retry_state(outcome, attempt_number=3, idle_for=1.234)

    # Patch Retrying in the module under test so we control the iteration and when before_sleep is invoked
    monkeypatch.setattr(models, "Retrying", FakeRetrying)

    # Prepare fake self and return value from _query; use n=None to exercise the n is None branch
    logged = []
    fake_return = [{"resp": "only"}, {"resp": "extra"}]
    fake_self = _make_fake_self(fake_return, logged)

    # Act: call the query function with n=None -> should return the first element
    result = models.LiteLLMModel.query(fake_self, history=None, n=None, temperature=0.5)

    # Assert return behavior (covers branch 784->786 when n is None)
    assert result == fake_return[0]

    # The before_sleep callback (retry_warning) should have been invoked from FakeAttempt.__exit__
    assert len(logged) == 1
    msg = logged[0]
    # Assertions target the formatting built in retry_warning: attempt number, slept seconds, and exception info
    assert "attempt 3" in msg
    assert "(slept for 1.23s)" in msg
    assert "due to Exception: boom" in msg


def test_retry_warning_no_exception_and_list_return_round_054(monkeypatch):
    # Arrange: produce a retry_state whose outcome is None -> exception_info should be empty
    models._TEST_RETRY_STATE = _make_retry_state(None, attempt_number=5, idle_for=2.5)

    # Patch Retrying to our fake implementation
    monkeypatch.setattr(models, "Retrying", FakeRetrying)

    # Prepare fake self and return value; use n==2 to exercise the return list branch
    logged = []
    fake_return = [{"x": 1}, {"x": 2}]
    fake_self = _make_fake_self(fake_return, logged)

    # Act: call the query function with n=2 -> should return the full list
    result = models.LiteLLMModel.query(fake_self, history=None, n=2, temperature=None)

    # Assert the function returns the whole list when n != 1 and not None
    assert result == fake_return

    # The retry warning should still have been called, but without the 'due to' exception text
    assert len(logged) == 1
    msg = logged[0]
    assert "attempt 5" in msg
    assert "(slept for 2.50s)" in msg
    assert "due to" not in msg
