import os
import types
import pytest

from sweagent.agent import models


class _SecretLike:
    def __init__(self, value: str):
        self._value = value

    def get_secret_value(self) -> str:
        return self._value


def test_api_key_none_round_045():
    """If api_key is None, get_api_keys should return an empty list."""
    # Create a lightweight object with the attribute the method expects
    self = types.SimpleNamespace()
    self.api_key = None

    result = models.GenericAPIModelConfig.get_api_keys(self)
    assert result == [], "Expected empty list when api_key is None"


def test_api_key_empty_string_round_045():
    """If api_key.get_secret_value() returns empty string, should return []."""
    self = types.SimpleNamespace()
    self.api_key = _SecretLike("")

    result = models.GenericAPIModelConfig.get_api_keys(self)
    assert result == [], "Expected empty list when secret value is empty"


def test_api_key_env_missing_round_045(monkeypatch):
    """If api_key refers to an env var (starts with $) and that env var is not set,
    the function should log a warning and return [].
    """
    env_name = "TEST_MISSING_ENV_VAR_ROUND_045"
    # Ensure the environment variable is not present
    monkeypatch.delenv(env_name, raising=False)

    # Replace get_logger in the module to capture the warning message
    recorded = {"warnings": []}

    def _fake_get_logger(name, emoji=None):
        class _L:
            def warning(self, msg):
                recorded["warnings"].append(msg)
        return _L()

    monkeypatch.setattr(models, "get_logger", _fake_get_logger)

    self = types.SimpleNamespace()
    # api_key string begins with $, so the code will attempt to read the env var
    self.api_key = _SecretLike(f"${env_name}")

    result = models.GenericAPIModelConfig.get_api_keys(self)
    assert result == [], "Expected empty list when referenced environment variable is not set"
    # Ensure the logged warning mentions the environment variable name
    assert any(env_name in msg for msg in recorded["warnings"]), (
        "Expected a warning that mentions the missing environment variable"
    )


def test_api_key_env_present_and_split_round_045(monkeypatch):
    """If api_key refers to an env var that is set, return the split keys.
    Also covers the path where the resolved api_key is split by ':::'.
    """
    env_name = "TEST_PRESENT_ENV_VAR_ROUND_045"
    monkeypatch.setenv(env_name, "keyA:::keyB")

    self = types.SimpleNamespace()
    self.api_key = _SecretLike(f"${env_name}")

    result = models.GenericAPIModelConfig.get_api_keys(self)
    assert result == ["keyA", "keyB"], "Expected environment value to be split on ':::'"
