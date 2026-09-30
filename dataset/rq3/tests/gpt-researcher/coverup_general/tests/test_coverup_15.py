# file: gpt_researcher/config/config.py:98-145
# asked: {"lines": [101, 102, 104, 106, 107, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 126, 133, 134, 135, 137, 138, 141, 142, 144, 145], "branches": [[100, 101], [111, 112], [111, 113], [113, 114], [113, 115], [115, 116], [115, 117], [117, 118], [117, 119], [119, 120], [119, 121], [121, 122], [121, 123], [123, 124], [123, 126], [132, 133], [140, 141], [143, 144]]}
# gained: {"lines": [101, 102, 104, 106, 107, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 126, 133, 134, 135, 137, 138, 141, 142, 144, 145], "branches": [[100, 101], [111, 112], [111, 113], [113, 114], [113, 115], [115, 116], [115, 117], [117, 118], [117, 119], [119, 120], [119, 121], [121, 122], [121, 123], [123, 124], [123, 126], [132, 133], [140, 141], [143, 144]]}

import warnings
import pytest

from gpt_researcher.config.config import Config


@pytest.mark.parametrize(
    "provider, extra_env, expected_model",
    [
        ("ollama", {"OLLAMA_EMBEDDING_MODEL": "ollama-model"}, "ollama-model"),
        ("custom", {"OPENAI_EMBEDDING_MODEL": "custom-model"}, "custom-model"),
        ("openai", {}, "text-embedding-3-large"),
        ("azure_openai", {}, "text-embedding-3-large"),
        ("huggingface", {}, "sentence-transformers/all-MiniLM-L6-v2"),
        ("gigachat", {}, "Embeddings"),
        ("google_genai", {}, "text-embedding-004"),
    ],
)
def test_embedding_provider_branches(monkeypatch, provider, extra_env, expected_model):
    """
    Test all embedding provider branches that set embedding_model based on EMBEDDING_PROVIDER.
    This also asserts that a deprecation FutureWarning is issued.
    """
    # Ensure a clean environment for relevant vars first
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
    monkeypatch.delenv("OLLAMA_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL", raising=False)

    # Prevent the deprecated handler from running during __init__
    original_handler = Config._handle_deprecated_attributes
    monkeypatch.setattr(Config, "_handle_deprecated_attributes", lambda self: None)

    cfg = Config()

    # Now set env vars for the branch
    monkeypatch.setenv("EMBEDDING_PROVIDER", provider)
    for k, v in extra_env.items():
        monkeypatch.setenv(k, v)

    # Restore original handler and call it under warnings capture
    monkeypatch.setattr(Config, "_handle_deprecated_attributes", original_handler)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        cfg._handle_deprecated_attributes()

        # One warning should have been emitted for EMBEDDING_PROVIDER deprecation
        assert any(
            isinstance(record.message, FutureWarning) and "EMBEDDING_PROVIDER is deprecated" in str(record.message)
            for record in w
        ), f"No FutureWarning for EMBEDDING_PROVIDER in warnings: {[str(x.message) for x in w]}"

    # Attributes should have been set according to the provider
    assert getattr(cfg, "embedding_provider") == provider
    assert getattr(cfg, "embedding_model") == expected_model


def test_embedding_provider_unknown_raises(monkeypatch):
    """
    If EMBEDDING_PROVIDER is set to an unknown value, the method should raise an Exception.
    Also ensure the deprecation warning is still emitted before the exception.
    """
    monkeypatch.delenv("EMBEDDING_PROVIDER", raising=False)
    monkeypatch.setenv("EMBEDDING_PROVIDER", "not_a_real_provider")

    # Prevent automatic execution during __init__
    original_handler = Config._handle_deprecated_attributes
    monkeypatch.setattr(Config, "_handle_deprecated_attributes", lambda self: None)
    cfg = Config()

    # Restore original and call, expecting an exception and a warning
    monkeypatch.setattr(Config, "_handle_deprecated_attributes", original_handler)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        with pytest.raises(Exception) as excinfo:
            cfg._handle_deprecated_attributes()

        # The raised exception should indicate provider not found
        assert "Embedding provider not found" in str(excinfo.value)

        # A deprecation FutureWarning should have been emitted prior to the exception
        assert any(isinstance(record.message, FutureWarning) and "EMBEDDING_PROVIDER is deprecated" in str(record.message) for record in w)


def test_llm_deprecation_and_model_envs(monkeypatch):
    """
    Test handling of deprecated LLM_PROVIDER, FAST_LLM_MODEL, and SMART_LLM_MODEL.
    Each set environment variable should cause a FutureWarning and update the config.
    """
    # Clean relevant envs first
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("FAST_LLM_MODEL", raising=False)
    monkeypatch.delenv("SMART_LLM_MODEL", raising=False)

    monkeypatch.setenv("LLM_PROVIDER", "legacy-llm")
    monkeypatch.setenv("FAST_LLM_MODEL", "fast-model-v1")
    monkeypatch.setenv("SMART_LLM_MODEL", "smart-model-v2")

    # Prevent automatic execution during __init__
    original_handler = Config._handle_deprecated_attributes
    monkeypatch.setattr(Config, "_handle_deprecated_attributes", lambda self: None)
    cfg = Config()

    # Restore original and call under warnings capture
    monkeypatch.setattr(Config, "_handle_deprecated_attributes", original_handler)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        cfg._handle_deprecated_attributes()

        # Expect at least three deprecation FutureWarnings for the deprecated vars
        fwarnings = [record for record in w if isinstance(record.message, FutureWarning) and "deprecated" in str(record.message).lower()]
        assert len(fwarnings) >= 3, f"Expected at least 3 deprecation warnings, got: {[str(x.message) for x in w]}"

    # The providers/models should have been set on the config instance
    assert getattr(cfg, "fast_llm_provider") == "legacy-llm"
    assert getattr(cfg, "smart_llm_provider") == "legacy-llm"
    assert getattr(cfg, "fast_llm_model") == "fast-model-v1"
    assert getattr(cfg, "smart_llm_model") == "smart-model-v2"
