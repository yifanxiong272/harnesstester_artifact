# file: aider/models.py:970-1022
# asked: {"lines": [972, 1008, 1013, 1014, 1015, 1016, 1019], "branches": [[971, 972], [983, 989], [1007, 1008], [1012, 1013], [1013, 1014], [1013, 1019]]}
# gained: {"lines": [972, 1008, 1013, 1014, 1015, 1016, 1019], "branches": [[971, 972], [1007, 1008], [1012, 1013], [1013, 1014]]}

import hashlib
import json
import types

import pytest

import aider.models as models


def test_send_completion_triggers_sanity_dump_and_github(monkeypatch):
    # Prepare flags and captured data
    sanity_called = {"v": False}
    ensure_called = {"v": False}
    dump_called = {"v": False, "kwargs": None}
    litellm_called = {"v": False, "kwargs": None}
    github_called = {"v": False, "headers": None}

    # Stub out model initialization helpers to keep __init__ simple and deterministic
    monkeypatch.setattr(models.Model, "get_model_info", lambda self, model: {"max_input_tokens": 1024})
    monkeypatch.setattr(models.Model, "validate_environment", lambda self: {"missing_keys": [], "keys_in_environment": {}})
    monkeypatch.setattr(models.Model, "configure_model_settings", lambda self, model: None)

    # Stub out sendchat utilities (these are imported into the module at import time)
    def sanity_stub(messages):
        sanity_called["v"] = True

    def ensure_stub(messages):
        ensure_called["v"] = True
        # Return a modified messages list so we can detect it downstream
        return [{"role": "system", "content": "ensured"}] + list(messages)

    monkeypatch.setattr(models, "sanity_check_messages", sanity_stub)
    monkeypatch.setattr(models, "ensure_alternating_roles", ensure_stub)

    # Stub dump to capture the kwargs it receives
    def dump_stub(kwargs):
        dump_called["v"] = True
        dump_called["kwargs"] = json.loads(json.dumps(kwargs))  # make sure it's JSON-serializable copy

    monkeypatch.setattr(models, "dump", dump_stub)

    # Stub litellm.completion to capture final kwargs and return a predictable response
    def litellm_stub(**kwargs):
        litellm_called["v"] = True
        # make a JSON-serializable copy for assertions
        litellm_called["kwargs"] = json.loads(json.dumps(kwargs))
        return {"result": "ok"}

    monkeypatch.setattr(models.litellm, "completion", litellm_stub)

    # Make Model behave as deepseek r1 and ollama for branches
    monkeypatch.setattr(models.Model, "is_deepseek_r1", lambda self: True)
    monkeypatch.setattr(models.Model, "is_ollama", lambda self: True)

    # token_count used to compute num_ctx for ollama branch
    monkeypatch.setattr(models.Model, "token_count", lambda self, messages: 100)

    # Replace github_copilot_token_to_open_ai_key with a stub that records headers
    def github_stub(self, extra_headers):
        github_called["v"] = True
        # record a copy
        github_called["headers"] = dict(extra_headers)

    monkeypatch.setattr(models.Model, "github_copilot_token_to_open_ai_key", github_stub)

    # Ensure environment variables that trigger branches are present
    monkeypatch.setenv("AIDER_SANITY_CHECK_TURNS", "1")
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN", "dummy-token")

    # Instantiate the model (weak_model and editor_model set to False to avoid extra calls)
    m = models.Model("test-model", weak_model=False, editor_model=False, verbose=True)

    # Ensure use_temperature is not False so the temperature branch runs.
    m.use_temperature = True

    # Ensure no extra_params (falsy) so the ollama num_ctx branch computes correctly
    m.extra_params = {}

    # Prepare messages and call send_completion with temperature=None to force the inner logic
    input_messages = [{"role": "user", "content": "hello"}]

    hash_obj, res = m.send_completion(messages=input_messages, functions=None, stream=False, temperature=None)

    # Assertions: sanity_check_messages and ensure_alternating_roles were invoked
    assert sanity_called["v"] is True
    assert ensure_called["v"] is True

    # dump should have been called because verbose=True
    assert dump_called["v"] is True
    # dump is called before messages are attached; ensure timeout is present in dumped kwargs
    assert "timeout" in dump_called["kwargs"]

    # litellm.completion should have been called and returned our stub response
    assert litellm_called["v"] is True
    assert res == {"result": "ok"}

    # The kwargs sent to litellm should include messages modified by ensure_alternating_roles
    assert "messages" in litellm_called["kwargs"]
    assert litellm_called["kwargs"]["messages"][0]["role"] == "system"
    assert litellm_called["kwargs"]["messages"][-1]["content"] == "hello"

    # Temperature branch: use_temperature was True, temperature was None -> temperature should be 0
    assert "temperature" in litellm_called["kwargs"]
    assert litellm_called["kwargs"]["temperature"] == 0

    # Ollama branch: num_ctx should be present and computed from token_count (100)
    expected_num_ctx = int(100 * 1.25) + 8192
    assert litellm_called["kwargs"].get("num_ctx") == expected_num_ctx

    # GitHub copilot branch: our github stub should have been called with extra_headers containing expected keys
    assert github_called["v"] is True
    assert "Editor-Version" in github_called["headers"]
    assert "Copilot-Integration-Id" in github_called["headers"]
    assert github_called["headers"]["Copilot-Integration-Id"] == "vscode-chat"

    # The function returns a hash object (sha1) as the first element; verify it behaves like one
    assert hasattr(hash_obj, "hexdigest")
    # Also verify the hexdigest is consistent with the kwargs used to create it (sorted JSON of kwargs at that time)
    # We can at least check it's a valid hex string of length 40 (sha1)
    h = hash_obj.hexdigest()
    assert isinstance(h, str) and len(h) == 40 and all(c in "0123456789abcdef" for c in h)
