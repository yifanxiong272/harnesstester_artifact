# file: aider/analytics.py:195-204
# asked: {"lines": [196, 197, 199, 200, 201, 202, 203, 204], "branches": [[196, 197], [196, 199], [200, 201], [200, 202], [202, 203], [202, 204]]}
# gained: {"lines": [196, 197, 199, 200, 201, 202, 203, 204], "branches": [[196, 197], [196, 199], [200, 201], [200, 202], [202, 203], [202, 204]]}

import pytest
from types import SimpleNamespace

import aider.analytics as analytics


class DummyModel:
    def __init__(self, name):
        self.name = name


def test_redact_model_name_returns_none_for_falsy_model():
    a = analytics.Analytics()
    assert a._redact_model_name(None) is None


def test_redact_model_name_returns_name_when_info_found(monkeypatch):
    called = {}

    def fake_get(name):
        called['name'] = name
        return {"some": "info"}  # truthy

    monkeypatch.setattr(analytics.model_info_manager, "get_model_from_cached_json_db", fake_get)

    a = analytics.Analytics()
    model = DummyModel("gpt-4")
    result = a._redact_model_name(model)
    assert result == "gpt-4"
    assert called.get('name') == "gpt-4"


def test_redact_model_name_redacts_when_slash_and_no_info(monkeypatch):
    def fake_get(name):
        # simulate not found
        return None

    monkeypatch.setattr(analytics.model_info_manager, "get_model_from_cached_json_db", fake_get)

    a = analytics.Analytics()
    model = DummyModel("openai/gpt-4")
    result = a._redact_model_name(model)
    assert result == "openai/REDACTED"


def test_redact_model_name_returns_none_when_no_info_and_no_slash(monkeypatch):
    def fake_get(name):
        return None

    monkeypatch.setattr(analytics.model_info_manager, "get_model_from_cached_json_db", fake_get)

    a = analytics.Analytics()
    model = DummyModel("unknownmodel")
    result = a._redact_model_name(model)
    assert result is None
