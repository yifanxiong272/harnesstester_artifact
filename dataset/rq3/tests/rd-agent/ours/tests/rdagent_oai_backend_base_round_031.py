import types
import re
import time
from datetime import datetime
import pytest
import json

import rdagent.oai.backend.base as base
from rdagent.core.exception import PolicyError

# Helper to call the unbound method with a fake self
def _call_method(fake_self, **kwargs):
    # The target is an unbound function on the class; call with fake_self
    return base.APIBackend._try_create_chat_completion_or_embedding(fake_self, **kwargs)


def make_fake_self():
    fake = types.SimpleNamespace()
    # default retry wait seconds used by function
    fake.retry_wait_seconds = 0
    return fake


def setup_defaults(monkeypatch):
    # Ensure deterministic no-op sleep
    sleep_calls = []

    def fake_sleep(s):
        sleep_calls.append(s)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    # Provide a simple truncate_content_list
    monkeypatch.setattr(base, "truncate_content_list", lambda lst, model: ["TRUNCATED"])

    # Provide default LLM_SETTINGS
    class DummySettings:
        max_retry = None
        embedding_model = "dummy-model"
        violation_fail_limit = 1
        timeout_fail_limit = 2
        embedding_max_length = 10

    monkeypatch.setattr(base, "LLM_SETTINGS", DummySettings)

    # Reset RD_Agent_TIMER_wrapper
    class DummyTimer:
        def __init__(self):
            self.started = False
            self.added = []

        def add_duration(self, dur):
            self.added.append(dur)

    dummy_wrapper = types.SimpleNamespace(api_fail_count=0, latest_api_fail_time=None, timer=DummyTimer())
    monkeypatch.setattr(base, "RD_Agent_TIMER_wrapper", dummy_wrapper)

    # Provide placeholder litellm and openai modules used only for isinstance checks
    class BadRequestError(Exception):
        pass

    class ContentPolicyViolationError(Exception):
        pass

    monkeypatch.setattr(base, "litellm", types.SimpleNamespace(BadRequestError=BadRequestError, ContentPolicyViolationError=ContentPolicyViolationError))

    class OpenAIErr(Exception):
        pass

    class APITimeoutError(OpenAIErr):
        pass

    class APIError(OpenAIErr):
        def __init__(self, message=None):
            super().__init__(message)
            self.message = message

    class RateLimitError(OpenAIErr):
        def __init__(self, message=None):
            super().__init__(message)
            self.message = message

    monkeypatch.setattr(base, "openai", types.SimpleNamespace(APITimeoutError=APITimeoutError, APIError=APIError, RateLimitError=RateLimitError))

    return sleep_calls


def test_embedding_success_round_031(monkeypatch):
    """Embedding path returns value directly when underlying method succeeds."""
    sleep_calls = setup_defaults(monkeypatch)

    fake_self = make_fake_self()

    # Provide a _create_embedding_with_cache that returns a deterministic embedding
    def create_embedding(*args, **kwargs):
        return [[0.1, 0.2]]

    fake_self._create_embedding_with_cache = create_embedding

    # Call with embedding True
    result = _call_method(fake_self, max_retry=3, embedding=True)
    assert result == [[0.1, 0.2]]
    # No sleep was requested for successful immediate return
    assert sleep_calls == []


def test_chat_success_round_031(monkeypatch):
    """Chat completion path returns value from auto continue method."""
    sleep_calls = setup_defaults(monkeypatch)

    fake_self = make_fake_self()

    def create_chat(*args, **kwargs):
        return "CHAT_OK"

    fake_self._create_chat_completion_auto_continue = create_chat

    result = _call_method(fake_self, max_retry=2, chat_completion=True)

    assert result == "CHAT_OK"
    assert sleep_calls == []


def test_embedding_truncation_then_success_round_031(monkeypatch):
    """If embedding raises a too-long error once, truncation is applied and retry succeeds."""
    sleep_calls = setup_defaults(monkeypatch)

    fake_self = make_fake_self()

    # Make the first call raise an Exception with a 'message' attribute that triggers too_long_error_message
    class TooLongError(Exception):
        def __init__(self, message):
            super().__init__(message)
            self.message = message

    calls = {"n": 0}

    def create_embedding(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TooLongError("input must have less than X tokens: too long")
        return [[9.9]]

    fake_self._create_embedding_with_cache = create_embedding

    # Provide original input_content_list so the function will mutate kwargs when truncating
    kwargs = {"input_content_list": ["a" * 1000]}

    result = _call_method(fake_self, max_retry=3, embedding=True, **kwargs)

    assert result == [[9.9]]
    # After truncation, kwargs passed to the function within would have been modified; ensure our provided dict still exists
    # The base function modifies its local kwargs; we verify truncate_content_list was used by calling create_embedding second time succeeded
    assert calls["n"] == 2
    # No long sleep occurred (retry_wait_seconds default 0)
    assert sleep_calls == []


def test_embedding_truncation_already_tried_raises_runtime_round_031(monkeypatch):
    """If embedding too-long error happens twice, a RuntimeError is raised with guidance."""
    setup_defaults(monkeypatch)

    fake_self = make_fake_self()

    class TooLongError(Exception):
        def __init__(self, message):
            super().__init__(message)
            self.message = message

    # Always raise the too-long style error
    def create_embedding(*args, **kwargs):
        raise TooLongError("maximum context length exceeded")

    fake_self._create_embedding_with_cache = create_embedding

    with pytest.raises(RuntimeError) as exc:
        _call_method(fake_self, max_retry=2, embedding=True, input_content_list=["x"])

    assert "Embedding failed even after truncation" in str(exc.value)


def test_chat_policy_violation_raises_policy_error_round_031(monkeypatch):
    """When openai is imported and a BadRequestError caused by content policy occurs, PolicyError is raised after limit."""
    setup_defaults(monkeypatch)

    fake_self = make_fake_self()

    # Create a litellm.BadRequestError instance with __cause__ ContentPolicyViolationError
    BadRequest = base.litellm.BadRequestError
    ContentPolicyErr = base.litellm.ContentPolicyViolationError

    class MyBadRequest(BadRequest):
        pass

    def create_chat(*args, **kwargs):
        e = MyBadRequest("bad request")
        # attach cause as a content policy violation
        e.__cause__ = ContentPolicyErr("policy")
        raise e

    fake_self._create_chat_completion_auto_continue = create_chat

    # Ensure module-level flag that simulates openai being available is True
    monkeypatch.setattr(base, "openai_imported", True)

    # violation_fail_limit default set by setup_defaults is 1
    with pytest.raises(PolicyError):
        _call_method(fake_self, max_retry=2, chat_completion=True)


def test_rate_limit_parsing_and_timer_round_031(monkeypatch):
    """When a RateLimitError with a retry-after message occurs, the recommended wait is parsed and timer adds duration."""
    sleep_calls = setup_defaults(monkeypatch)

    fake_self = make_fake_self()
    fake_self.retry_wait_seconds = 7  # default if parsing fails would be this

    # Create an exception instance whose message contains the recommended seconds
    RateLimitErr = base.openai.RateLimitError

    class MyRateLimit(RateLimitErr):
        pass

    calls = {"n": 0}

    def create_chat(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            e = MyRateLimit("Please retry after 3 seconds.")
            # attach message attribute used by the code
            e.message = "Please retry after 3 seconds."
            raise e
        return "AFTER_RETRY"

    fake_self._create_chat_completion_auto_continue = create_chat

    # Make sure openai_imported True and timer started so add_duration is invoked
    monkeypatch.setattr(base, "openai_imported", True)
    base.RD_Agent_TIMER_wrapper.timer.started = True

    result = _call_method(fake_self, max_retry=3, chat_completion=True)

    assert result == "AFTER_RETRY"
    # Confirm the sleep was invoked with the parsed 3 seconds
    assert sleep_calls == [3]
    # The timer should have recorded at least one duration add
    assert len(base.RD_Agent_TIMER_wrapper.timer.added) >= 1
