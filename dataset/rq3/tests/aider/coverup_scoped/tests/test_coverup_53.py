# file: aider/analytics.py:195-204
# asked: {"lines": [196, 197, 199, 200, 201, 202, 203, 204], "branches": [[196, 197], [196, 199], [200, 201], [200, 202], [202, 203], [202, 204]]}
# gained: {"lines": [196, 197, 199, 200, 201, 202, 203, 204], "branches": [[196, 197], [196, 199], [200, 201], [200, 202], [202, 203], [202, 204]]}

import pytest

from types import SimpleNamespace

import aider.analytics as analytics_mod
from aider.analytics import Analytics


def make_model(name):
    return SimpleNamespace(name=name)


def test_redact_model_name_none():
    a = Analytics.__new__(Analytics)  # avoid running __init__
    assert a._redact_model_name(None) is None


def test_redact_model_name_found_in_db(monkeypatch):
    a = Analytics.__new__(Analytics)
    model = make_model("gpt-4")

    def fake_get(name):
        # simulate found in cached json db (truthy)
        return {"name": name}

    monkeypatch.setattr(
        analytics_mod.model_info_manager,
        "get_model_from_cached_json_db",
        fake_get,
    )

    assert a._redact_model_name(model) == "gpt-4"


def test_redact_model_name_slash_not_in_db(monkeypatch):
    a = Analytics.__new__(Analytics)
    model = make_model("org/modelA")

    def fake_get(name):
        # simulate not found
        return None

    monkeypatch.setattr(
        analytics_mod.model_info_manager,
        "get_model_from_cached_json_db",
        fake_get,
    )

    assert a._redact_model_name(model) == "org/REDACTED"


def test_redact_model_name_not_in_db_no_slash(monkeypatch):
    a = Analytics.__new__(Analytics)
    model = make_model("unknown-model")

    def fake_get(name):
        # simulate not found
        return None

    monkeypatch.setattr(
        analytics_mod.model_info_manager,
        "get_model_from_cached_json_db",
        fake_get,
    )

    assert a._redact_model_name(model) is None
