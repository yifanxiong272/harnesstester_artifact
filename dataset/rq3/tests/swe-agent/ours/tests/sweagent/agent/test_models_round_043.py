import os
import types
import pytest

from sweagent.agent import models


class _DummySecret:
    def __init__(self, val: str | None):
        self._val = val

    def get_secret_value(self) -> str | None:
        return self._val


class _SpyLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, msg: str):
        # record message for assertions
        self.warnings.append(msg)


def test_api_key_none_round_043():
    """When api_key is None the method should return an empty list."""
    dummy = types.SimpleNamespace()
    dummy.api_key = None

    result = models.GenericAPIModelConfig.get_api_keys(dummy)
    assert result == []


def test_api_key_empty_secret_round_043():
    """When SecretStr.get_secret_value() returns an empty string -> returns []."""
    dummy = types.SimpleNamespace()
    dummy.api_key = _DummySecret("")

    result = models.GenericAPIModelConfig.get_api_keys(dummy)
    assert result == []


def test_api_key_direct_multi_keys_round_043():
    """When api_key is a plain value with ':::' delimiter, it should be split into list."""
    dummy = types.SimpleNamespace()
    dummy.api_key = _DummySecret("alpha:::beta:::gamma")

    result = models.GenericAPIModelConfig.get_api_keys(dummy)
    assert result == ["alpha", "beta", "gamma"]


def test_api_key_env_var_not_set_logs_warning_round_043(monkeypatch):
    """When api_key starts with '$' and env var missing -> logs a warning and returns []."""
    # ensure env var is not present
    monkeypatch.delenv("MISSING_ENV_FOR_TEST", raising=False)

    dummy = types.SimpleNamespace()
    dummy.api_key = _DummySecret("$MISSING_ENV_FOR_TEST")

    spy = _SpyLogger()

    # Patch the module-level get_logger to return our spy instance so we can assert on warnings.
    monkeypatch.setattr(models, "get_logger", lambda *a, **k: spy)

    result = models.GenericAPIModelConfig.get_api_keys(dummy)
    assert result == []
    # Verify that a warning mentioning the environment variable name was emitted.
    assert any("MISSING_ENV_FOR_TEST" in w for w in spy.warnings)


def test_api_key_env_var_set_multi_keys_round_043(monkeypatch):
    """When api_key starts with '$' and env var set to 'a:::b' -> returns split list."""
    monkeypatch.setenv("MY_KEYS_VAR", "one:::two")

    dummy = types.SimpleNamespace()
    dummy.api_key = _DummySecret("$MY_KEYS_VAR")

    # Patch get_logger to a no-op logger to avoid noise; not expecting warnings here.
    monkeypatch.setattr(models, "get_logger", lambda *a, **k: _SpyLogger())

    result = models.GenericAPIModelConfig.get_api_keys(dummy)
    assert result == ["one", "two"]
