# file: aider/models.py:728-765
# asked: {"lines": [757, 758, 759, 760, 761, 762, 763, 765], "branches": [[754, 757], [758, 759], [758, 760], [760, 761], [760, 762], [762, 763], [762, 765]]}
# gained: {"lines": [757, 758, 759, 760, 761, 762, 763, 765], "branches": [[754, 757], [758, 759], [758, 760], [760, 761], [760, 762], [762, 763], [762, 765]]}

import os
import pytest

from aider import models


def _setup_common(monkeypatch, provider, litellm_res):
    # Ensure fast validation does not short-circuit
    monkeypatch.setattr(models.Model, "fast_validate_environment", lambda self: {})
    # Provide model info with desired provider and safe max_input_tokens
    monkeypatch.setattr(
        models.Model,
        "get_model_info",
        lambda self, model: {"litellm_provider": provider, "max_input_tokens": 0},
    )
    # Avoid side effects from model configuration
    monkeypatch.setattr(models.Model, "configure_model_settings", lambda self, model: None)
    # Make litellm.validate_environment return the desired structure
    monkeypatch.setattr(models.litellm, "validate_environment", lambda model: dict(litellm_res))


@pytest.mark.parametrize(
    "provider,env_var,expected_missing,expected_keys_in_env",
    [
        ("cohere_chat", "COHERE_API_KEY", ["COHERE_API_KEY"], False),
        ("gemini", "GEMINI_API_KEY", ["GEMINI_API_KEY"], False),
        ("groq", "GROQ_API_KEY", ["GROQ_API_KEY"], False),
    ],
)
def test_provider_branches_missing_keys(monkeypatch, provider, env_var, expected_missing, expected_keys_in_env):
    """
    For each provider branch when the corresponding API env var is absent,
    validate_environment should delegate to validate_variables and report the var as missing.
    """
    # litellm should indicate no missing keys and not having keys in environment so provider check runs
    litellm_res = {"keys_in_environment": False, "missing_keys": []}
    _setup_common(monkeypatch, provider, litellm_res)

    # Ensure the environment variable is not present
    monkeypatch.delenv(env_var, raising=False)

    m = models.Model("test-model", weak_model=False, editor_model=False)

    # The constructor sets these based on validate_environment's returned dict
    assert m.missing_keys == expected_missing
    assert m.keys_in_environment is expected_keys_in_env


@pytest.mark.parametrize(
    "provider,env_var",
    [
        ("cohere_chat", "COHERE_API_KEY"),
        ("gemini", "GEMINI_API_KEY"),
        ("groq", "GROQ_API_KEY"),
    ],
)
def test_provider_branches_present_keys(monkeypatch, provider, env_var):
    """
    For each provider branch when the corresponding API env var is present,
    validate_environment should delegate to validate_variables and report keys_in_environment True.
    """
    litellm_res = {"keys_in_environment": False, "missing_keys": []}
    _setup_common(monkeypatch, provider, litellm_res)

    # Set the environment variable to simulate presence
    monkeypatch.setenv(env_var, "dummy-key")

    m = models.Model("test-model", weak_model=False, editor_model=False)

    assert m.missing_keys == []
    assert m.keys_in_environment is True


def test_non_matching_provider_returns_litellm_res(monkeypatch):
    """
    If the provider is not one of the special cases, validate_environment should
    return the original litellm.validate_environment result unchanged.
    """
    provider = "something_else"
    # Use a litellm response that indicates keys_in_environment False and no missing keys
    litellm_res = {"keys_in_environment": False, "missing_keys": []}
    _setup_common(monkeypatch, provider, litellm_res)

    m = models.Model("test-model", weak_model=False, editor_model=False)

    # Because provider doesn't match, constructor should have stored the original litellm result
    assert m.missing_keys == []
    assert m.keys_in_environment is False
