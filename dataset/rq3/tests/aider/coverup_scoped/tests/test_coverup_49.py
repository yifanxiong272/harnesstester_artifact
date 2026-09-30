# file: aider/models.py:728-765
# asked: {"lines": [757, 758, 759, 760, 761, 762, 763, 765], "branches": [[754, 757], [758, 759], [758, 760], [760, 761], [760, 762], [762, 763], [762, 765]]}
# gained: {"lines": [757, 758, 759, 760, 761, 762, 763, 765], "branches": [[754, 757], [758, 759], [758, 760], [760, 761], [760, 762], [762, 763], [762, 765]]}

import pytest
import types

import aider.models as models


@pytest.fixture(autouse=True)
def ensure_clean_env(monkeypatch):
    # Ensure tests don't depend on real environment variables
    # and restore any monkeypatching after each test.
    yield


def make_model_instance(monkeypatch, provider_value, litellm_res):
    """
    Create a Model instance without running its __init__ and prepare it
    so that validate_environment will execute the provider branch logic.
    """
    Model = models.Model
    inst = Model.__new__(Model)
    # Ensure fast_validate_environment returns falsy so main logic runs
    inst.fast_validate_environment = lambda: None
    # minimal required attributes used by validate_environment
    inst.name = "some-model"
    inst.info = {"litellm_provider": provider_value}
    # Patch litellm.validate_environment to return desired structure
    monkeypatch.setattr(models.litellm, "validate_environment", lambda model: dict(litellm_res))
    return inst


def test_cohere_provider_calls_validate_variables(monkeypatch):
    called = []

    def fake_validate_variables(vars):
        called.append(list(vars))
        # simulate missing
        return {"keys_in_environment": False, "missing_keys": ["COHERE_API_KEY"]}

    monkeypatch.setattr(models, "validate_variables", fake_validate_variables)

    inst = make_model_instance(monkeypatch, "cohere_chat", {"keys_in_environment": False, "missing_keys": []})
    res = inst.validate_environment()

    assert called == [["COHERE_API_KEY"]], "validate_variables should be called with COHERE_API_KEY for cohere_chat"
    assert res == {"keys_in_environment": False, "missing_keys": ["COHERE_API_KEY"]}


@pytest.mark.parametrize("provider,expected_var", [
    ("gemini", ["GEMINI_API_KEY"]),
    ("groq", ["GROQ_API_KEY"]),
    ("CoHeRe_ChAt", ["COHERE_API_KEY"]),  # case-insensitive check
])
def test_provider_variants_trigger_expected_validation(monkeypatch, provider, expected_var):
    called = []

    def fake_validate_variables(vars):
        called.append(list(vars))
        return {"keys_in_environment": True, "missing_keys": []}

    monkeypatch.setattr(models, "validate_variables", fake_validate_variables)

    inst = make_model_instance(monkeypatch, provider, {"keys_in_environment": False, "missing_keys": []})
    res = inst.validate_environment()

    assert called == [expected_var], f"validate_variables should be called with {expected_var} for provider {provider}"
    assert res == {"keys_in_environment": True, "missing_keys": []}


def test_non_matching_provider_returns_litellm_result(monkeypatch):
    # When provider not matched, should return the litellm.validate_environment result unchanged
    litellm_result = {"keys_in_environment": False, "missing_keys": []}
    inst = make_model_instance(monkeypatch, "something_else", litellm_result)
    # Ensure validate_variables won't be accidentally called
    monkeypatch.setattr(models, "validate_variables", lambda vars: (_ for _ in ()).throw(AssertionError("validate_variables should not be called")))
    res = inst.validate_environment()
    assert res == litellm_result
