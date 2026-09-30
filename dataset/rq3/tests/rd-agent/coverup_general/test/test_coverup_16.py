# file: rdagent/oai/backend/base.py:457-550
# asked: {"lines": [466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 483, 485, 486, 489, 490, 492, 493, 496, 497, 498, 502, 503, 505, 507, 508, 510, 512, 514, 515, 516, 519, 520, 521, 522, 524, 526, 528, 529, 530, 531, 534, 535, 536, 537, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550], "branches": [[471, 472], [471, 549], [474, 475], [474, 476], [476, 471], [476, 477], [479, 483], [479, 485], [489, 490], [489, 507], [490, 492], [490, 502], [510, 519], [510, 524], [520, 521], [520, 524], [524, 534], [524, 539], [535, 536], [535, 539], [540, 541], [540, 544], [542, 543], [542, 544], [545, 546], [545, 547]]}
# gained: {"lines": [466, 467, 468, 469, 470, 471, 472, 473, 474, 475, 476, 477, 478, 479, 480, 481, 485, 486, 489, 490, 492, 493, 496, 497, 498, 502, 503, 505, 507, 508, 510, 512, 524, 526, 528, 539, 540, 541, 542, 543, 544, 545, 546, 547, 548, 549, 550], "branches": [[471, 472], [471, 549], [474, 475], [474, 476], [476, 477], [479, 485], [489, 490], [489, 507], [490, 492], [490, 502], [510, 524], [524, 539], [540, 541], [540, 544], [542, 543], [545, 546], [545, 547]]}

import pytest
import types

import rdagent.oai.backend.base as base_mod
from rdagent.oai.backend.base import APIBackend


def _make_concrete_backend(overrides: dict = None):
    """
    Helper to create a minimal concrete subclass of APIBackend implementing required abstract methods.
    We allow passing overrides to set custom methods for testing.
    """
    overrides = overrides or {}

    class Concrete(APIBackend):
        def _calculate_token_from_messages(self, messages):
            return 0

        def _create_chat_completion_inner_function(self, *args, **kwargs):
            return overrides.get("_create_chat_completion_inner_function_result", "inner")

        def _create_embedding_inner_function(self, *args, **kwargs):
            return overrides.get("_create_embedding_inner_function_result", [])

        def supports_response_schema(self):
            return overrides.get("supports_response_schema_result", False)

    # attach any override callables onto the class so instances can use them
    for name, val in overrides.items():
        if callable(val):
            setattr(Concrete, name, val)
    return Concrete


def test_assert_both_true_raises_assertion():
    Concrete = _make_concrete_backend()

    class B(Concrete):
        def _create_embedding_with_cache(self, *args, **kwargs):
            return []

        def _create_chat_completion_auto_continue(self, *args, **kwargs):
            return "ok"

    b = B()
    with pytest.raises(AssertionError):
        b._try_create_chat_completion_or_embedding(chat_completion=True, embedding=True)


def test_embedding_truncate_then_fail(monkeypatch):
    # Make retries small
    monkeypatch.setattr(base_mod.LLM_SETTINGS, "max_retry", 2)
    monkeypatch.setattr(base_mod.LLM_SETTINGS, "embedding_model", "test-model")

    from rdagent.oai.utils.embedding import truncate_content_list

    original_content = ["one", "two", "three", "four", "five"]
    expected_truncated = truncate_content_list(original_content, "test-model")

    class TooLongError(Exception):
        pass

    def make_exc():
        e = TooLongError("too long")
        e.message = "maximum context length exceeded"
        return e

    Concrete = _make_concrete_backend()

    class B(Concrete):
        def __init__(self):
            self.calls = 0
            self.received_on_call = []
            super().__init__()

        def _create_embedding_with_cache(self, *args, **kwargs):
            self.calls += 1
            self.received_on_call.append(kwargs.get("input_content_list", None))
            raise make_exc()

    b = B()
    # ensure retry_wait_seconds exists and small
    b.retry_wait_seconds = 0

    with pytest.raises(RuntimeError) as excinfo:
        b._try_create_chat_completion_or_embedding(embedding=True, input_content_list=original_content)

    assert b.calls >= 2
    # Second call should have the truncated content
    assert b.received_on_call[1] == expected_truncated
    assert "Please set LLM_SETTINGS.embedding_max_length" in str(excinfo.value)


def test_chat_completion_rate_limit_parsing_and_timer(monkeypatch):
    # Limit retries
    monkeypatch.setattr(base_mod.LLM_SETTINGS, "max_retry", 2)

    # Fake openai module and mark openai_imported True
    class FakeOpenAI:
        class RateLimitError(Exception):
            pass

        class APITimeoutError(Exception):
            pass

        class APIError(Exception):
            def __init__(self, msg=""):
                super().__init__(msg)
                self.message = msg

    fake_openai = FakeOpenAI()
    monkeypatch.setattr(base_mod, "openai", fake_openai)
    monkeypatch.setattr(base_mod, "openai_imported", True)

    # Patch time.sleep to record sleeps
    slept = []

    def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(base_mod, "time", types.SimpleNamespace(sleep=fake_sleep))

    # Fake timer
    class FakeTimer:
        def __init__(self):
            self.started = True
            self.durations = []

        def add_duration(self, d):
            self.durations.append(d)

    fake_timer = FakeTimer()
    monkeypatch.setattr(base_mod.RD_Agent_TIMER_wrapper, "timer", fake_timer)
    monkeypatch.setattr(base_mod.RD_Agent_TIMER_wrapper, "api_fail_count", 0)
    monkeypatch.setattr(base_mod.RD_Agent_TIMER_wrapper, "latest_api_fail_time", None)

    Concrete = _make_concrete_backend()

    class B(Concrete):
        def __init__(self):
            self.calls = 0
            super().__init__()

        def _create_chat_completion_auto_continue(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                e = fake_openai.RateLimitError("rate limited")
                e.message = "Please retry after 2 seconds."
                raise e
            return "succeeded"

    b = B()
    # ensure attribute exists and can be modified
    b.retry_wait_seconds = 0
    result = b._try_create_chat_completion_or_embedding(chat_completion=True)

    assert result == "succeeded"
    assert slept and slept[0] == 2
    assert len(fake_timer.durations) == 1
    assert base_mod.RD_Agent_TIMER_wrapper.latest_api_fail_time is not None


def test_exhaust_retries_raises_final_runtime_error(monkeypatch):
    monkeypatch.setattr(base_mod.LLM_SETTINGS, "max_retry", 3)
    monkeypatch.setattr(base_mod, "time", types.SimpleNamespace(sleep=lambda s: None))

    Concrete = _make_concrete_backend()

    class B(Concrete):
        def __init__(self):
            super().__init__()

        def _create_chat_completion_auto_continue(self, *args, **kwargs):
            raise Exception("generic failure")

    b = B()
    b.retry_wait_seconds = 0
    with pytest.raises(RuntimeError) as excinfo:
        b._try_create_chat_completion_or_embedding(chat_completion=True)

    assert f"Failed to create chat completion after {base_mod.LLM_SETTINGS.max_retry} retries." in str(excinfo.value)
