import hashlib
import json
import types

import pytest

from aider import models as models_mod


def make_bare_model():
    # Create an instance without running __init__ to avoid heavy construction
    M = models_mod.Model
    m = object.__new__(M)
    # Provide minimal attributes used by send_completion
    m.name = "test-model"
    m.use_temperature = False
    m.extra_params = None
    m.verbose = False
    m.is_deepseek_r1 = lambda: False
    m.is_ollama = lambda: False
    m.token_count = lambda messages: 1
    # placeholder; tests will override if they need to capture calls
    m.github_copilot_token_to_open_ai_key = lambda headers: None
    return m


def test_send_completion_sanity_and_temperature_and_verbose_round_165(monkeypatch):
    called = {}

    # Ensure sanity-check branch triggers
    monkeypatch.setenv("AIDER_SANITY_CHECK_TURNS", "1")

    def fake_sanity_check_messages(messages):
        called['sanity'] = list(messages)

    monkeypatch.setattr(models_mod, "sanity_check_messages", fake_sanity_check_messages)

    # capture dump calls when verbose
    def fake_dump(obj):
        called.setdefault('dump', []).append(obj)

    monkeypatch.setattr(models_mod, "dump", fake_dump)

    # capture litellm.completion kwargs and return a sentinel
    completion_called = {}

    def fake_completion(**kwargs):
        completion_called['kwargs'] = kwargs.copy()
        return {'ok': True}

    monkeypatch.setattr(models_mod.litellm, "completion", fake_completion)

    # Build a model instance that will hit the temperature branch (use_temperature True)
    m = make_bare_model()
    m.use_temperature = True
    m.verbose = True

    messages = [{"role": "user", "content": "hello"}]

    # Call with temperature=None to exercise the path where a boolean use_temperature sets 0
    returned_hash, returned_res = models_mod.Model.send_completion(m, messages, functions=None, stream=False, temperature=None)

    # sanity_check_messages should have been called with the messages
    assert 'sanity' in called and called['sanity'] == messages

    # dump should have been called (verbose True)
    assert 'dump' in called and isinstance(called['dump'][0], dict)

    # litellm.completion should have been called and returned value propagated
    assert returned_res == {'ok': True}
    assert 'kwargs' in completion_called

    # The kwargs passed to completion must include messages and a timeout (added later in function)
    passed_kwargs = completion_called['kwargs']
    assert passed_kwargs['messages'] is messages
    assert 'timeout' in passed_kwargs
    # Because use_temperature was True and temperature arg was None, temperature should be set to 0
    assert passed_kwargs['temperature'] == 0

    # The returned hash_object should match the sha1 of the kwargs snapshot used to build the key
    # In the function the key is computed before adding timeout and messages; replicate that
    initial_kwargs = {"model": m.name, "stream": False, "temperature": 0}
    expected_hash = hashlib.sha1(json.dumps(initial_kwargs, sort_keys=True).encode())
    assert isinstance(returned_hash, hashlib.sha1.__mro__[0].__class__) or hasattr(returned_hash, 'hexdigest')
    assert returned_hash.hexdigest() == expected_hash.hexdigest()


def test_send_completion_github_copilot_round_165(monkeypatch):
    called = {}

    # Ensure the GITHUB_COPILOT_TOKEN presence triggers the extra headers branch
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN", "dummy-token")

    # Patch litellm.completion to capture the kwargs passed
    completion_called = {}

    def fake_completion(**kwargs):
        completion_called['kwargs'] = kwargs.copy()
        return {'copilot': True}

    monkeypatch.setattr(models_mod.litellm, "completion", fake_completion)

    # Create a model and patch its github conversion method to record calls
    m = make_bare_model()

    def fake_github_to_openai(headers):
        called['copilot_headers'] = headers.copy()

    m.github_copilot_token_to_open_ai_key = fake_github_to_openai

    # use_temperature False to skip temperature handling in this test
    m.use_temperature = False
    m.verbose = False

    messages = [{"role": "user", "content": "whoami"}]

    returned_hash, returned_res = models_mod.Model.send_completion(m, messages, functions=None, stream=True, temperature=0.5)

    # The copilot conversion should have been called with the extra_headers dict added by the function
    assert 'copilot_headers' in called
    hdrs = called['copilot_headers']
    # It should include the expected keys
    assert hdrs["Editor-Version"].startswith("aider/")
    assert hdrs["Copilot-Integration-Id"] == "vscode-chat"

    # The completion should have been invoked and its return propagated
    assert returned_res == {'copilot': True}
    assert 'kwargs' in completion_called
    passed_kwargs = completion_called['kwargs']
    # Confirm extra_headers made it into the final kwargs passed to the completion call
    assert 'extra_headers' in passed_kwargs and isinstance(passed_kwargs['extra_headers'], dict)
    assert passed_kwargs['messages'] is messages
