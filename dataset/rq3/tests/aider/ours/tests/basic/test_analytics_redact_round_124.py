import pytest

import aider.analytics as analytics_mod
from aider.analytics import Analytics


class DummyModel:
    def __init__(self, name):
        self.name = name


def _make_analytics_instance():
    # Create an Analytics instance without invoking its __init__ (no external effects)
    return object.__new__(Analytics)


def test_redact_model_name_none_round_124():
    a = _make_analytics_instance()
    # When model is falsy (None), should return None
    assert a._redact_model_name(None) is None


def test_redact_model_name_info_present_round_124(monkeypatch):
    a = _make_analytics_instance()

    # Patch the model_info_manager on the analytics module to return a truthy info
    class StubManager:
        def get_model_from_cached_json_db(self, name):
            # return a truthy object to simulate model known in cache
            return {"cached": True, "name": name}

    monkeypatch.setattr(analytics_mod, "model_info_manager", StubManager())

    model = DummyModel("gpt-4")
    # If info is present, the original model name should be returned
    assert a._redact_model_name(model) == "gpt-4"


def test_redact_model_name_redact_slash_round_124(monkeypatch):
    a = _make_analytics_instance()

    # Patch to return falsy (None) so code follows the slash-redaction branch
    class StubManager:
        def get_model_from_cached_json_db(self, name):
            return None

    monkeypatch.setattr(analytics_mod, "model_info_manager", StubManager())

    model = DummyModel("provider/some-model")
    # Expect the provider prefix kept and the rest replaced with REDACTED
    assert a._redact_model_name(model) == "provider/REDACTED"


def test_redact_model_name_no_slash_no_info_round_124(monkeypatch):
    a = _make_analytics_instance()

    # Patch to return falsy so we hit the final fallback branch when no slash present
    class StubManager:
        def get_model_from_cached_json_db(self, name):
            return None

    monkeypatch.setattr(analytics_mod, "model_info_manager", StubManager())

    model = DummyModel("unknown-model")
    # No cached info and no slash -> should return None
    assert a._redact_model_name(model) is None
