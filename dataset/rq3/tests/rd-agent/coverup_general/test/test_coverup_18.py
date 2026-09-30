# file: rdagent/oai/backend/base.py:562-649
# asked: {"lines": [577, 578, 581, 582, 583, 584, 585, 587, 588, 589, 590, 591, 592, 593, 596, 597, 599, 601, 602, 603, 604, 605, 606, 607, 608, 609, 611, 612, 613, 614, 616, 619, 621, 622, 623, 626, 627, 628, 632, 633, 634, 635, 637, 639, 640, 642, 643, 644, 646, 647, 648, 649], "branches": [[577, 578], [577, 581], [581, 582], [581, 583], [587, 588], [587, 596], [589, 590], [589, 596], [590, 591], [590, 593], [602, 603], [602, 616], [603, 604], [603, 606], [612, 613], [612, 614], [619, 621], [619, 632], [622, 623], [622, 626], [627, 628], [627, 632], [632, 633], [632, 639], [635, 637], [635, 639], [639, 640], [639, 647], [640, 642], [640, 643], [643, 644], [643, 646], [647, 648], [647, 649]]}
# gained: {"lines": [577, 578, 581, 583, 584, 585, 587, 588, 589, 590, 591, 592, 593, 596, 597, 599, 601, 602, 603, 604, 605, 606, 607, 608, 609, 611, 612, 613, 614, 616, 619, 621, 622, 623, 632, 633, 634, 635, 639, 640, 642, 643, 644, 646, 647, 648, 649], "branches": [[577, 578], [577, 581], [581, 583], [587, 588], [587, 596], [589, 590], [590, 591], [602, 603], [602, 616], [603, 604], [603, 606], [612, 613], [612, 614], [619, 621], [619, 632], [622, 623], [632, 633], [632, 639], [635, 639], [639, 640], [640, 642], [640, 643], [643, 644], [643, 646], [647, 648], [647, 649]]}

import json
import re
import pytest
from pydantic import BaseModel

import rdagent.oai.backend.base as base_mod
from rdagent.oai.backend.base import APIBackend


class SimpleBackend(APIBackend):
    def __init__(self, *args, **kwargs):
        # Force parent init but avoid creating real sqlite cache by disabling cache flags
        super().__init__(use_chat_cache=False, dump_chat_cache=False)

        # Allow tests to set these attributes after instantiation if needed
        self._inner_responses = []  # list of tuples (response, finish_reason)
        self.added_json_in_prompt = False

    def supports_response_schema(self) -> bool:
        return True

    def _calculate_token_from_messages(self, messages):
        return 1

    def _create_embedding_inner_function(self, input_content_list):
        return [[0.1, 0.2] for _ in input_content_list]

    def _create_chat_completion_inner_function(self, messages, response_format=None, **kwargs):
        # Pop next response from list, or return a default full response
        if self._inner_responses:
            return self._inner_responses.pop(0)
        return ("{\"default\": true}", None)

    def _add_json_in_prompt(self, messages):
        # Mark that it was called and mutate messages for assertion
        self.added_json_in_prompt = True
        messages.append({"role": "system", "content": "[JSON_SCHEMA_ADDED]"})


def test_cached_response_returns_and_logs(monkeypatch):
    backend = SimpleBackend()

    # Ensure seed generator not used in this scenario
    monkeypatch.setattr(base_mod.LLM_SETTINGS, "use_auto_chat_cache_seed_gen", False)
    monkeypatch.setattr(base_mod.LLM_SETTINGS, "log_llm_chat_content", True)

    # Create fake cache and attach to backend, enable use_chat_cache
    called = {"get_called_with": None, "get_returned": "CACHED_ANS"}

    class FakeCache:
        def chat_get(self_inner, key):
            called["get_called_with"] = key
            return called["get_returned"]

        def chat_set(self_inner, key, val):
            # not expected in this test
            raise AssertionError("chat_set should not be called in cached test")

    backend.use_chat_cache = True
    backend.cache = FakeCache()

    # Provide a deterministic seed so input_content_json is predictable
    out = backend._create_chat_completion_auto_continue(messages=[{"role": "user", "content": "hi"}], seed=42)
    assert out == "CACHED_ANS"
    # ensure cache was queried and seed included in the cache key
    assert "<seed=42/>" in called["get_called_with"]


def test_retry_exhaust_raises_runtime_error(monkeypatch):
    # Make sure we don't touch caching or seed generation
    monkeypatch.setattr(base_mod.LLM_SETTINGS, "use_auto_chat_cache_seed_gen", False)

    backend = SimpleBackend()
    backend.use_chat_cache = False

    # Force inner function to always return finish_reason "length" to exhaust retries
    backend._inner_responses = [("part", "length")] * 6

    with pytest.raises(RuntimeError) as exc:
        backend._create_chat_completion_auto_continue(messages=[{"role": "user", "content": "x"}])
    assert "Failed to continue the conversation" in str(exc.value)


def test_json_mode_think_removal_parse_and_dump_cache(monkeypatch):
    backend = SimpleBackend()
    backend.use_chat_cache = False

    # Arrange LLM_SETTINGS for think removal
    monkeypatch.setattr(base_mod.LLM_SETTINGS, "reasoning_think_rm", True)
    # Ensure top-of-function sets response_format when json_mode True
    # Provide a fake parser.parse that will be used
    parsed_out = '{"ok": true}'

    class FakeParser:
        def __init__(self, add_json_in_prompt=False):
            self.add_json_in_prompt = add_json_in_prompt

        def parse(self, text):
            # confirm that parse receives the expected trimmed JSON text
            assert '{"ok": true}' in text or '{"ok":true}' in text
            return parsed_out

    monkeypatch.setattr(base_mod, "JSONParser", FakeParser)

    # Prepare inner function to return a message containing <think>... and JSON after it
    backend._inner_responses = [("<think>internal reasoning</think>{\"ok\":true}", None)]

    # Prepare fake cache and enable dump
    cache_calls = {"set": []}

    class FakeCache2:
        def chat_get(self_inner, key):
            return None

        def chat_set(self_inner, key, val):
            cache_calls["set"].append((key, val))

    backend.cache = FakeCache2()
    backend.dump_chat_cache = True

    # Call with json_mode True and add_json_in_prompt True to exercise _add_json_in_prompt
    out = backend._create_chat_completion_auto_continue(
        messages=[{"role": "user", "content": "please output json"}],
        json_mode=True,
        add_json_in_prompt=True,
    )
    # The fake parser returns parsed_out; ensure it is returned
    assert out == parsed_out
    # ensure dump to cache happened once and stored the returned string
    assert len(cache_calls["set"]) == 1
    assert cache_calls["set"][0][1] == parsed_out
    # ensure _add_json_in_prompt was invoked and mutated messages (backend keeps track)
    assert backend.added_json_in_prompt is True


def test_pydantic_response_format_validation_and_unknown_format_warning(monkeypatch):
    # Ensure deterministic behavior for seed generation
    monkeypatch.setattr(base_mod.LLM_SETTINGS, "use_auto_chat_cache_seed_gen", False)

    backend = SimpleBackend()
    backend.use_chat_cache = False

    # 1) Test with a pydantic model class as response_format
    class RespModel(BaseModel):
        a: int

    backend._inner_responses = [(" {\"a\": 123} ", None)]
    # No JSONParser involvement; directly the pydantic branch will parse json.loads and instantiate
    result = backend._create_chat_completion_auto_continue(
        messages=[{"role": "user", "content": "give json"}],
        response_format=RespModel,
    )
    # Should return the raw all_response built from inner responses
    assert "{\"a\": 123}" in result or '"a": 123' in result

    # 2) Test unknown response_format triggers warning path but still returns content
    # Use a dummy class (not a subclass of BaseModel) so issubclass check runs safely
    class DummyFormat:
        pass

    backend._inner_responses = [("final text", None)]
    backend.dump_chat_cache = False
    out2 = backend._create_chat_completion_auto_continue(
        messages=[{"role": "user", "content": "give text"}],
        response_format=DummyFormat,
    )
    assert out2 == "final text"
