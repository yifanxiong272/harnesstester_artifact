import json
import sys
import types
import pytest
from types import SimpleNamespace
import os

import aider.models as models_module


def _bound_method():
    # Bind the unbound function to a dummy instance so we avoid constructing Model
    return models_module.Model.github_copilot_token_to_open_ai_key.__get__(object(), models_module.Model)


def _make_fake_requests(status_code=200, text='{}', json_obj=None):
    if json_obj is None:
        json_obj = {}

    class DummyResponse:
        def __init__(self, status_code, text, json_obj):
            self.status_code = status_code
            self.text = text
            self._json = json_obj

        def json(self):
            return self._json

    def get(url, headers=None):
        return DummyResponse(status_code, text, json_obj)

    return SimpleNamespace(get=get)


def test_missing_github_token_round_042(monkeypatch):
    # Ensure OPENAI_API_KEY is absent and GITHUB_COPILOT_TOKEN not set
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('GITHUB_COPILOT_TOKEN', raising=False)

    # Provide a stub requests module so the function can import it if it reaches that line
    monkeypatch.setitem(sys.modules, 'requests', _make_fake_requests())

    fn = _bound_method()
    extra = {"Editor-Version": "v", "Copilot-Integration-Id": "id"}

    with pytest.raises(KeyError) as exc:
        fn(extra)

    assert "GITHUB_COPILOT_TOKEN environment variable not found" in str(exc.value)


def test_empty_github_token_round_042(monkeypatch):
    # OPENAI_API_KEY absent so it will try to use GitHub Copilot token
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setenv('GITHUB_COPILOT_TOKEN', '   ')

    # Stub requests to avoid network access
    monkeypatch.setitem(sys.modules, 'requests', _make_fake_requests())

    fn = _bound_method()
    extra = {"Editor-Version": "v", "Copilot-Integration-Id": "id"}

    with pytest.raises(KeyError) as exc:
        fn(extra)

    assert "GITHUB_COPILOT_TOKEN environment variable is empty" in str(exc.value)


def test_non_200_response_round_042(monkeypatch):
    # Simulate a non-200 response from the GitHub Copilot API and assert the error message
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    github_token = 'abcdef12345'
    monkeypatch.setenv('GITHUB_COPILOT_TOKEN', github_token)

    fake = _make_fake_requests(status_code=403, text='{"error":"forbidden"}', json_obj={"error": "forbidden"})
    monkeypatch.setitem(sys.modules, 'requests', fake)

    fn = _bound_method()
    extra = {"Editor-Version": "v1", "Copilot-Integration-Id": "cid"}

    with pytest.raises(Exception) as exc:
        fn(extra)

    msg = str(exc.value)
    # Expect status, URL and a safe token preview (first 5 chars + ...)
    assert "Status: 403" in msg
    assert "https://api.github.com/copilot_internal/v2/token" in msg
    assert github_token[:5] + "..." in msg
    # Authorization header in the printed safe headers should not include the full token
    assert github_token not in msg or github_token.endswith('...')


def test_missing_token_field_round_042(monkeypatch):
    # Simulate 200 OK but missing 'token' key in response JSON
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setenv('GITHUB_COPILOT_TOKEN', 'goodtoken')

    fake = _make_fake_requests(status_code=200, text='{"ok":true}', json_obj={})
    monkeypatch.setitem(sys.modules, 'requests', fake)

    fn = _bound_method()
    extra = {"Editor-Version": "v", "Copilot-Integration-Id": "id"}

    with pytest.raises(Exception) as exc:
        fn(extra)

    assert "Response missing 'token' field" in str(exc.value)


def test_success_sets_openai_api_key_round_042(monkeypatch):
    # Simulate successful token retrieval and verify environment variable set
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setenv('GITHUB_COPILOT_TOKEN', 'goodtoken123')

    fake = _make_fake_requests(status_code=200, text='{"token":"new-openai-key"}', json_obj={"token": "new-openai-key"})
    monkeypatch.setitem(sys.modules, 'requests', fake)

    fn = _bound_method()
    extra = {"Editor-Version": "1.2.3", "Copilot-Integration-Id": "integration-xyz"}

    # Call should set OPENAI_API_KEY in the environment
    fn(extra)

    assert os.environ.get('OPENAI_API_KEY') == 'new-openai-key'
