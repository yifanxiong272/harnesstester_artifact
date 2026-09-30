import json
from types import SimpleNamespace
import pytest

import rdagent.oai.backend.base as base_mod


class FakeCache:
    def __init__(self, get_result=None):
        self.get_result = get_result
        self.last_get_key = None
        self.last_set = None

    def chat_get(self, key):
        self.last_get_key = key
        return self.get_result

    def chat_set(self, key, value):
        self.last_set = (key, value)


class DummyJSONParser:
    def __init__(self, add_json_in_prompt=False):
        self.add_json_in_prompt = add_json_in_prompt

    def parse(self, content):
        # Return python object if valid json-like string, otherwise return raw string
        if isinstance(content, dict):
            return content
        try:
            return json.loads(content)
        except Exception:
            # fallback: if content already looks like dict repr, return as dict
            if isinstance(content, str) and content.startswith('{') and content.endswith('}'):
                # crude safe eval
                return json.loads(content.replace("'", '"'))
            return content


class DummyTypeAdapter:
    def __init__(self, target):
        self.target = target

    def validate_json(self, payload):
        # emulate validation: raise if payload missing required key if target is str 'REQUIRE_KEY'
        if self.target == 'REQUIRE_KEY' and 'must' not in payload:
            raise ValueError('missing must')
        return True


def make_fake_self(cache=None, use_chat_cache=False, dump_chat_cache=False):
    self = SimpleNamespace()
    self.use_chat_cache = use_chat_cache
    self.dump_chat_cache = dump_chat_cache
    self.cache = cache or FakeCache()

    # helper hooks that the method may call; tests will monkeypatch these when needed
    def _add_json_in_prompt(messages):
        # add a marker to indicate it was called
        messages.append({'role': 'system', 'content': '<json_prompt_added/>'})

    self._add_json_in_prompt = _add_json_in_prompt

    return self


def test_cache_hit_returns_cached_result_round_023(monkeypatch):
    # Arrange: make LLM_SETTINGS indicate seed generation and log content
    monkeypatch.setattr(base_mod, 'LLM_CACHE_SEED_GEN', SimpleNamespace(get_next_seed=lambda: 42))
    monkeypatch.setattr(base_mod, 'LLM_SETTINGS', SimpleNamespace(use_auto_chat_cache_seed_gen=True, log_llm_chat_content=True, reasoning_think_rm=False))

    fake_cache = FakeCache(get_result='CACHED!')
    self = make_fake_self(cache=fake_cache, use_chat_cache=True)

    # Call the underlying function with messages that will be stringified
    messages = [{'role': 'user', 'content': 'hello'}]

    # Act
    result = base_mod.APIBackend._create_chat_completion_auto_continue(self, messages, json_mode=True, chat_cache_prefix='prefix-', seed=None)

    # Assert
    assert result == 'CACHED!'
    # Ensure cache key included the generated seed and prefix
    expected_input_json = 'prefix-' + json.dumps(messages) + '<seed=42/>'
    assert fake_cache.last_get_key == expected_input_json


def test_complete_flow_json_parse_and_dump_cache_round_023(monkeypatch):
    # Arrange: no cache hit, enable seed generation for determinism
    monkeypatch.setattr(base_mod, 'LLM_CACHE_SEED_GEN', SimpleNamespace(get_next_seed=lambda: 7))
    # Enable reasoning trimming and auto seed; enable logging flags off to avoid noise
    monkeypatch.setattr(base_mod, 'LLM_SETTINGS', SimpleNamespace(use_auto_chat_cache_seed_gen=True, log_llm_chat_content=False, reasoning_think_rm=True))

    # Replace JSONParser and TypeAdapter used in the module with our dummies
    monkeypatch.setattr(base_mod, 'JSONParser', lambda add_json_in_prompt=False: DummyJSONParser(add_json_in_prompt=add_json_in_prompt))
    monkeypatch.setattr(base_mod, 'TypeAdapter', lambda target: DummyTypeAdapter(target))

    # Prepare cache that returns no hit initially and capture set
    fake_cache = FakeCache(get_result=None)
    self = make_fake_self(cache=fake_cache, use_chat_cache=True, dump_chat_cache=True)

    # Replace the inner function to return a response that contains a <think>..</think> wrapper
    def inner_fn(messages, response_format=None, **kwargs):
        # Return a response that includes a <think> block and then a json body
        return ('<think>internal reasoning</think>{"ok": true}', 'stop')

    self._create_chat_completion_inner_function = inner_fn

    # Also patch _add_json_in_prompt to verify it's called when add_json_in_prompt=True
    called = {'added': False}

    def add_json(messages):
        called['added'] = True
        messages.append({'role': 'system', 'content': '<json/>'})

    self._add_json_in_prompt = add_json

    messages = [{'role': 'user', 'content': 'give me json'}]

    # Act
    out = base_mod.APIBackend._create_chat_completion_auto_continue(self, messages, json_mode=True, add_json_in_prompt=True, chat_cache_prefix='X-', seed=None)

    # Assert: because of reasoning_think_rm, the <think>...</think> is stripped and parser.parse converts JSON to dict
    assert isinstance(out, dict)
    assert out.get('ok') is True
    # ensure _add_json_in_prompt was called
    assert called['added'] is True
    # Ensure cache.set was invoked and stored the parsed response
    assert fake_cache.last_set is not None
    expected_key = 'X-' + json.dumps(messages[:-1]) + '<seed=7/>'
    # messages was mutated by add_json to have an appended system entry; the cache key is built from the original messages at start of call
    # ensure the last_set value equals the parsed dict
    assert fake_cache.last_set[1] == out


def test_retry_exhausts_and_raises_round_023(monkeypatch):
    # Arrange: no cache to ensure we enter retry loop
    monkeypatch.setattr(base_mod, 'LLM_SETTINGS', SimpleNamespace(use_auto_chat_cache_seed_gen=False, log_llm_chat_content=False, reasoning_think_rm=False))
    fake_cache = FakeCache(get_result=None)
    self = make_fake_self(cache=fake_cache, use_chat_cache=False, dump_chat_cache=False)

    # inner function always returns finish_reason 'length' to exhaust retries
    def inner_fn_length(messages, response_format=None, **kwargs):
        return ('partial', 'length')

    self._create_chat_completion_inner_function = inner_fn_length

    messages = [{'role': 'user', 'content': 'short'}]

    # Act & Assert: should raise RuntimeError after exhausting try_n
    with pytest.raises(RuntimeError) as exc:
        base_mod.APIBackend._create_chat_completion_auto_continue(self, messages, json_mode=False, add_json_in_prompt=False, chat_cache_prefix='')
    assert 'Failed to continue the conversation' in str(exc.value)
