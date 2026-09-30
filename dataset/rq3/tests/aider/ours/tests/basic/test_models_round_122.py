import pytest

from aider import models


class FakeSelf:
    """Minimal self-like object with the attributes used by
    Model.validate_environment. We call the unbound function
    models.Model.validate_environment(fake_self) so the object only
    needs name, info, and fast_validate_environment()."""

    def __init__(self, name: str, provider: str):
        self.name = name
        self.info = {"litellm_provider": provider}

    def fast_validate_environment(self):
        # Return falsy so the function proceeds to call litellm.validate_environment
        return None


def test_cohere_chat_round_122(monkeypatch):
    # Arrange: make litellm.validate_environment return a res dict with no missing keys
    res = {"missing_keys": [], "keys_in_environment": False}
    monkeypatch.setattr(models.litellm, "validate_environment", lambda model: res)

    # Patch validate_variables to return a distinct sentinel so we can assert the branch
    sentinel = {"provider_checked": "cohere"}
    monkeypatch.setattr(models, "validate_variables", lambda vars: sentinel)

    fake = FakeSelf(name="any-model", provider="cohere_chat")

    # Act
    out = models.Model.validate_environment(fake)

    # Assert: provider branch for cohere_chat is taken and the patched validate_variables result is returned
    assert out is sentinel


def test_gemini_round_122(monkeypatch):
    res = {"missing_keys": [], "keys_in_environment": False}
    monkeypatch.setattr(models.litellm, "validate_environment", lambda model: res)

    sentinel = {"provider_checked": "gemini"}
    monkeypatch.setattr(models, "validate_variables", lambda vars: sentinel)

    fake = FakeSelf(name="any-model", provider="gemini")

    out = models.Model.validate_environment(fake)

    assert out is sentinel


def test_groq_round_122(monkeypatch):
    res = {"missing_keys": [], "keys_in_environment": False}
    monkeypatch.setattr(models.litellm, "validate_environment", lambda model: res)

    sentinel = {"provider_checked": "groq"}
    monkeypatch.setattr(models, "validate_variables", lambda vars: sentinel)

    fake = FakeSelf(name="any-model", provider="groq")

    out = models.Model.validate_environment(fake)

    assert out is sentinel


def test_default_provider_returns_res_round_122(monkeypatch):
    # If provider does not match any special strings, the function should return the res dict from litellm.validate_environment
    res = {"missing_keys": [], "keys_in_environment": False, "marker": "original_res"}
    monkeypatch.setattr(models.litellm, "validate_environment", lambda model: res)

    # Ensure validate_variables is not invoked (if it were, it would return something different)
    monkeypatch.setattr(models, "validate_variables", lambda vars: {"unexpected": True})

    fake = FakeSelf(name="any-model", provider="not_a_real_provider")

    out = models.Model.validate_environment(fake)

    assert out is res
