import importlib
import re
import json
import types
import pytest

# Load the module under test
base_mod = importlib.import_module("rdagent.oai.backend.base")
APIBackend_try = base_mod.APIBackend._try_create_chat_completion_or_embedding


class SimpleTimer:
    def __init__(self):
        self.started = False
        self.added = False

    def add_duration(self, _):
        self.added = True


class DummyTimerWrapper:
    def __init__(self):
        self.timer = SimpleTimer()
        self.api_fail_count = 0
        self.latest_api_fail_time = None


class FakeBackend:
    """A minimal object providing attributes and callables used by
    APIBackend._try_create_chat_completion_or_embedding. We call the
    function as an unbound function passing an instance of this class
    as the 'self' parameter to avoid needing to fully construct the
    real APIBackend."""

    def __init__(self):
        # default wait seconds used when regex doesn't match
        self.retry_wait_seconds = 1

    # These methods will be monkeypatched in tests to simulate behavior
    def _create_embedding_with_cache(self, *args, **kwargs):
        raise NotImplementedError

    def _create_chat_completion_auto_continue(self, *args, **kwargs):
        raise NotImplementedError


def _make_settings(**kwargs):
    # Create a simple object to stand in for LLM_SETTINGS
    obj = types.SimpleNamespace()
    # default fields used in the function under test
    obj.max_retry = kwargs.get("max_retry", None)
    obj.violation_fail_limit = kwargs.get("violation_fail_limit", 3)
    obj.timeout_fail_limit = kwargs.get("timeout_fail_limit", 3)
    obj.embedding_model = kwargs.get("embedding_model", "mock-model")
    obj.embedding_max_length = kwargs.get("embedding_max_length", 100)
    return obj


def test_assertion_both_true_round_032():
    backend = FakeBackend()
    # Both True should raise the assertion at the start of the function
    with pytest.raises(AssertionError):
        APIBackend_try(backend, max_retry=1, chat_completion=True, embedding=True)


def test_embedding_return_round_032():
    backend = FakeBackend()

    # Provide an embedding result and ensure it is returned directly
    def return_embedding(*args, **kwargs):
        return [[0.1, 0.2]]

    backend._create_embedding_with_cache = return_embedding

    # Ensure LLM_SETTINGS does not override our max_retry
    base_mod.LLM_SETTINGS = _make_settings(max_retry=None)

    result = APIBackend_try(backend, max_retry=1, embedding=True)
    assert result == [[0.1, 0.2]]


def test_chat_completion_return_round_032():
    backend = FakeBackend()

    def return_chat(*args, **kwargs):
        return "chat-ok"

    backend._create_chat_completion_auto_continue = return_chat

    base_mod.LLM_SETTINGS = _make_settings(max_retry=None)

    result = APIBackend_try(backend, max_retry=1, chat_completion=True)
    assert result == "chat-ok"


def test_embedding_too_long_truncation_then_fail_round_032(monkeypatch):
    """Simulate an embedding provider raising a 'too long' error twice.
    The code should attempt truncation the first time and on the second
    occurrence raise a RuntimeError with guidance."""

    backend = FakeBackend()

    class TooLongError(Exception):
        pass

    def raise_too_long(*args, **kwargs):
        e = TooLongError("embedding too long")
        # set .message attribute to satisfy hasattr(e, 'message') checks
        e.message = "maximum context length exceeded"
        raise e

    backend._create_embedding_with_cache = raise_too_long

    # Provide a truncate_content_list that records it was called and returns truncated content
    called = {}

    def fake_truncate_content_list(original, model_name):
        called['truncated'] = True
        # return a clearly modified list
        return ["TRUNCATED"]

    monkeypatch.setattr(base_mod, "truncate_content_list", fake_truncate_content_list)

    # Ensure LLM_SETTINGS does not override max_retry passed in
    monkeypatch.setattr(base_mod, "LLM_SETTINGS", _make_settings(max_retry=None))

    # Call with embedding True and an input_content_list to be truncated
    with pytest.raises(RuntimeError) as excinfo:
        APIBackend_try(backend, max_retry=2, embedding=True, input_content_list=["long" * 1000])

    # The RuntimeError should mention truncation guidance
    assert "Embedding failed even after truncation" in str(excinfo.value)
    # And our truncate helper should have been invoked on first catch
    assert called.get('truncated', False) is True


def test_rate_limit_sets_recommended_wait_and_timer_update_round_032(monkeypatch):
    """Simulate a RateLimitError carrying a 'Please retry after N seconds.'
    message so the regex extracts the wait seconds, sleep is called with
    that value, and RD_Agent_TIMER_wrapper.timer.add_duration gets invoked."""

    backend = FakeBackend()

    # Create mock exception classes expected by the implementation
    class MockRateLimitError(Exception):
        pass

    class MockAPITimeoutError(Exception):
        pass

    class MockAPIError(Exception):
        pass

    def raise_rate_limit(*args, **kwargs):
        e = MockRateLimitError("rate limited")
        # Provide .message for compatibility with code
        e.message = "Please retry after 7 seconds."
        raise e

    backend._create_chat_completion_auto_continue = raise_rate_limit

    # Patch openai_imported and openai with all attributes the code may access
    monkeypatch.setattr(base_mod, "openai_imported", True)
    mock_openai = types.SimpleNamespace(
        RateLimitError=MockRateLimitError,
        APITimeoutError=MockAPITimeoutError,
        APIError=MockAPIError,
    )
    monkeypatch.setattr(base_mod, "openai", mock_openai)

    # Ensure LLM_SETTINGS does not override max_retry passed in
    monkeypatch.setattr(base_mod, "LLM_SETTINGS", _make_settings(max_retry=None))

    # Replace time.sleep with a spy to capture the recommended wait seconds
    sleep_calls = []

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(base_mod, "time", types.SimpleNamespace(sleep=fake_sleep))

    # Replace RD_Agent_TIMER_wrapper with a controllable fake
    fake_wrapper = DummyTimerWrapper()
    fake_wrapper.timer.started = True
    monkeypatch.setattr(base_mod, "RD_Agent_TIMER_wrapper", fake_wrapper)

    # Provide a no-op logger to avoid clutter
    monkeypatch.setattr(base_mod, "logger", types.SimpleNamespace(warning=lambda *a, **k: None))

    # Run and expect a final RuntimeError after retries exhausted
    with pytest.raises(RuntimeError):
        APIBackend_try(backend, max_retry=1, chat_completion=True)

    # Verify sleep was called with the integer parsed from the message
    assert sleep_calls == [7]
    # And the fake timer should have recorded add_duration being called (True)
    assert fake_wrapper.timer.added is True
