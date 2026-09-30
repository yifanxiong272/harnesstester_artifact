import os
import warnings
import pytest
from gpt_researcher.config.config import Config


def _make_config_stub():
    # Create a Config instance without running __init__ so we can set attributes deterministically
    cfg = object.__new__(Config)
    # Provide minimal attributes used by _handle_deprecated_attributes
    cfg.embedding_provider = "default_provider"
    cfg.embedding_model = None
    cfg.fast_llm_provider = "fast_default"
    cfg.fast_llm_model = "fast_model_default"
    cfg.smart_llm_provider = "smart_default"
    cfg.smart_llm_model = "smart_model_default"
    return cfg


def test_embedding_ollama_round_026(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_EMBEDDING_MODEL", "ollama-embed-v1")

    cfg = _make_config_stub()

    with pytest.warns(FutureWarning):
        cfg._handle_deprecated_attributes()

    assert cfg.embedding_provider == "ollama"
    assert cfg.embedding_model == "ollama-embed-v1"


def test_embedding_custom_round_026(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "custom")
    # Ensure OPENAI_EMBEDDING_MODEL is not set to exercise the getenv default
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL", raising=False)

    cfg = _make_config_stub()

    with pytest.warns(FutureWarning):
        cfg._handle_deprecated_attributes()

    assert cfg.embedding_provider == "custom"
    # default fallback (from getenv default) expected to be 'custom'
    assert cfg.embedding_model == "custom"


def test_embedding_openai_round_026(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")

    cfg = _make_config_stub()

    with pytest.warns(FutureWarning):
        cfg._handle_deprecated_attributes()

    assert cfg.embedding_provider == "openai"
    assert cfg.embedding_model == "text-embedding-3-large"


def test_embedding_azure_openai_round_026(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "azure_openai")

    cfg = _make_config_stub()

    with pytest.warns(FutureWarning):
        cfg._handle_deprecated_attributes()

    assert cfg.embedding_provider == "azure_openai"
    assert cfg.embedding_model == "text-embedding-3-large"


def test_embedding_huggingface_round_026(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "huggingface")

    cfg = _make_config_stub()

    with pytest.warns(FutureWarning):
        cfg._handle_deprecated_attributes()

    assert cfg.embedding_provider == "huggingface"
    assert cfg.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"


def test_embedding_gigachat_round_026(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "gigachat")

    cfg = _make_config_stub()

    with pytest.warns(FutureWarning):
        cfg._handle_deprecated_attributes()

    assert cfg.embedding_provider == "gigachat"
    assert cfg.embedding_model == "Embeddings"


def test_embedding_google_genai_round_026(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "google_genai")

    cfg = _make_config_stub()

    with pytest.warns(FutureWarning):
        cfg._handle_deprecated_attributes()

    assert cfg.embedding_provider == "google_genai"
    assert cfg.embedding_model == "text-embedding-004"


def test_embedding_unknown_raises_round_026(monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "__unknown_provider__")

    cfg = _make_config_stub()

    # The code first emits a deprecation warning and then raises for unknown provider
    with pytest.warns(FutureWarning):
        with pytest.raises(Exception) as excinfo:
            cfg._handle_deprecated_attributes()
    assert "Embedding provider not found." in str(excinfo.value)


def test_llm_provider_deprecation_sets_providers_round_026(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "legacy-llm")

    cfg = _make_config_stub()
    # ensure different initial values so we can observe the change
    cfg.fast_llm_provider = "before_fast"
    cfg.smart_llm_provider = "before_smart"

    with pytest.warns(FutureWarning):
        cfg._handle_deprecated_attributes()

    assert cfg.fast_llm_provider == "legacy-llm"
    assert cfg.smart_llm_provider == "legacy-llm"


def test_fast_and_smart_llm_model_deprecation_round_026(monkeypatch):
    # Test FAST_LLM_MODEL
    monkeypatch.setenv("FAST_LLM_MODEL", "fast-model-v2")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    cfg = _make_config_stub()
    cfg.fast_llm_model = "orig_fast"

    with pytest.warns(FutureWarning):
        cfg._handle_deprecated_attributes()

    assert cfg.fast_llm_model == "fast-model-v2"

    # Test SMART_LLM_MODEL
    monkeypatch.setenv("SMART_LLM_MODEL", "smart-model-v9")
    cfg = _make_config_stub()
    cfg.smart_llm_model = "orig_smart"

    with pytest.warns(FutureWarning):
        cfg._handle_deprecated_attributes()

    assert cfg.smart_llm_model == "smart-model-v9"
