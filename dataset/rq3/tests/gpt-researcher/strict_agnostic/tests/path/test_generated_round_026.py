import warnings
import os
import pytest
from gpt_researcher.config.config import Config

class DummyConfig:
    def __init__(self):
        # defaults to observe when env values are applied or preserved
        self.embedding_provider = "orig_embed"
        self.embedding_model = "orig_model"
        self.fast_llm_provider = "orig_fast"
        self.smart_llm_provider = "orig_smart"
        self.fast_llm_model = "orig_fast_model"
        self.smart_llm_model = "orig_smart_model"


def test_embedding_ollama_round_026(monkeypatch):
    """When EMBEDDING_PROVIDER=ollama and OLLAMA_EMBEDDING_MODEL is set,
    the deprecated handling should set embedding_provider and embedding_model
    and emit a FutureWarning."""
    dummy = DummyConfig()
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_EMBEDDING_MODEL", "ollama-model-123")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        # call unbound function with dummy instance as self
        Config._handle_deprecated_attributes(dummy)

        # a deprecation warning must be emitted for EMBEDDING_PROVIDER
        assert any(isinstance(x.message, Warning) for x in w)
        # ensure the specific attribute values changed as expected
        assert dummy.embedding_provider == "ollama"
        assert dummy.embedding_model == "ollama-model-123"


def test_embedding_custom_default_round_026(monkeypatch):
    """When EMBEDDING_PROVIDER=custom and OPENAI_EMBEDDING_MODEL is not set,
    the code should set embedding_model to the getenv default 'custom'."""
    dummy = DummyConfig()
    monkeypatch.setenv("EMBEDDING_PROVIDER", "custom")
    # ensure OPENAI_EMBEDDING_MODEL is absent
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL", raising=False)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        Config._handle_deprecated_attributes(dummy)
        # deprecation warning emitted
        assert any(isinstance(x.message, Warning) for x in w)
        # embedding_model should be the default 'custom'
        assert dummy.embedding_model == "custom"
        assert dummy.embedding_provider == "custom"


def test_embedding_unknown_raises_round_026(monkeypatch):
    """An unknown EMBEDDING_PROVIDER must raise the explicit Exception.
    This exercises the fallback/else branch that raises.
    """
    dummy = DummyConfig()
    monkeypatch.setenv("EMBEDDING_PROVIDER", "some-unsupported-provider")

    with pytest.raises(Exception) as excinfo:
        Config._handle_deprecated_attributes(dummy)
    assert "Embedding provider not found" in str(excinfo.value)


def test_llm_deprecated_and_model_envs_round_026(monkeypatch):
    """When LLM_PROVIDER, FAST_LLM_MODEL and SMART_LLM_MODEL env vars are present,
    the function should set fast/smart providers and models and emit warnings.
    """
    dummy = DummyConfig()
    monkeypatch.setenv("LLM_PROVIDER", "legacy-llm")
    monkeypatch.setenv("FAST_LLM_MODEL", "fast-legacy-model")
    monkeypatch.setenv("SMART_LLM_MODEL", "smart-legacy-model")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        Config._handle_deprecated_attributes(dummy)

        # should have emitted multiple deprecation warnings (at least one)
        assert any(isinstance(x.message, Warning) for x in w)

        # providers should be taken from the LLM_PROVIDER env var
        assert dummy.fast_llm_provider == "legacy-llm"
        assert dummy.smart_llm_provider == "legacy-llm"

        # models should be taken from respective env vars
        assert dummy.fast_llm_model == "fast-legacy-model"
        assert dummy.smart_llm_model == "smart-legacy-model"
