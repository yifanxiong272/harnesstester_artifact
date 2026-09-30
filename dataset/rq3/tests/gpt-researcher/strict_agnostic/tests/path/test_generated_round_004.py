import sys
import types
import os
import pytest

from gpt_researcher.memory.embeddings import Memory

# Helper to create fake modules with embedding classes
def _make_langchain_openai_module():
    mod = types.ModuleType("langchain_openai")

    class OpenAIEmbeddings:
        def __init__(self, *args, **kwargs):
            # Accept either model positional or model kw
            self.args = args
            self.kwargs = kwargs
            self.model = kwargs.get("model") if "model" in kwargs else (args[0] if args else None)
            self.openai_api_key = kwargs.get("openai_api_key")
            self.openai_api_base = kwargs.get("openai_api_base")
            # capture any other kwargs to assert forwarding
            self.extra = {k: v for k, v in kwargs.items() if k not in ("model", "openai_api_key", "openai_api_base")}

    class AzureOpenAIEmbeddings:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.model = kwargs.get("model") if "model" in kwargs else (args[0] if args else None)
            # expected azure-specific params
            self.azure_endpoint = kwargs.get("azure_endpoint")
            self.openai_api_key = kwargs.get("openai_api_key")
            self.openai_api_version = kwargs.get("openai_api_version")

    # Export classes
    setattr(mod, "OpenAIEmbeddings", OpenAIEmbeddings)
    setattr(mod, "AzureOpenAIEmbeddings", AzureOpenAIEmbeddings)
    return mod


def _make_langchain_ollama_module():
    mod = types.ModuleType("langchain_ollama")

    class OllamaEmbeddings:
        def __init__(self, *args, **kwargs):
            # Ollama called with model=model and base_url from env
            self.args = args
            self.kwargs = kwargs
            self.model = kwargs.get("model") if "model" in kwargs else (args[0] if args else None)
            self.base_url = kwargs.get("base_url")

    setattr(mod, "OllamaEmbeddings", OllamaEmbeddings)
    return mod


def _inject_fake_providers(monkeypatch):
    # Insert fake modules into sys.modules so runtime imports in Memory.__init__ resolve to these fakes
    monkeypatch.setitem(sys.modules, "langchain_openai", _make_langchain_openai_module())
    monkeypatch.setitem(sys.modules, "langchain_ollama", _make_langchain_ollama_module())


def test_providers_round_004(monkeypatch):
    """Exercise several provider branches (custom, openai (env override), azure_openai, ollama).

    This test injects fake provider implementations and controls environment variables so the
    Memory.__init__ import-time branching and env-dependent behavior can be asserted.
    """
    # Prepare fake modules
    _inject_fake_providers(monkeypatch)

    # Set environment variables used by the branches deterministically
    monkeypatch.setenv("OPENAI_API_KEY", "TEST_OPENAI_KEY")
    # Use distinct OPENAI_BASE_URL to verify both custom and openai paths pick it up when appropriate
    monkeypatch.setenv("OPENAI_BASE_URL", "http://env-openai-base.local/v1")

    # Azure expected vars
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://azure.example")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "AZURE_KEY")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2023-08-01")

    # Ollama expected var
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.local")

    # 1) custom provider: should construct OpenAIEmbeddings and pick up the env OPENAI_API_KEY and OPENAI_BASE_URL
    mem_custom = Memory("custom", "custom-model", extra_custom=1)
    emb_custom = mem_custom._embeddings
    # Confirm an instance of our fake OpenAIEmbeddings was created
    assert type(emb_custom).__name__ == "OpenAIEmbeddings"
    # model should be passed
    assert emb_custom.model == "custom-model"
    # custom branch uses OPENAI_API_KEY env value
    assert emb_custom.openai_api_key == "TEST_OPENAI_KEY"
    # custom branch uses OPENAI_BASE_URL env as default base
    assert emb_custom.openai_api_base == "http://env-openai-base.local/v1"
    # forwarded kwargs are present
    assert emb_custom.extra.get("extra_custom") == 1

    # 2) openai provider: ensure that when OPENAI_BASE_URL is set and no 'openai_api_base' in kwargs,
    # embedding_kwargs gets populated from the env variable
    mem_openai = Memory("openai", "openai-model")
    emb_openai = mem_openai._embeddings
    assert type(emb_openai).__name__ == "OpenAIEmbeddings"
    assert emb_openai.model == "openai-model"
    # openai branch should have gained openai_api_base from env
    assert emb_openai.openai_api_base == "http://env-openai-base.local/v1"

    # 3) azure_openai provider: should construct AzureOpenAIEmbeddings and pull azure-specific env vars
    mem_azure = Memory("azure_openai", "azure-model")
    emb_azure = mem_azure._embeddings
    assert type(emb_azure).__name__ == "AzureOpenAIEmbeddings"
    assert emb_azure.model == "azure-model"
    assert emb_azure.azure_endpoint == "https://azure.example"
    assert emb_azure.openai_api_key == "AZURE_KEY"
    # azure version should match AZURE_OPENAI_API_VERSION
    assert emb_azure.openai_api_version == "2023-08-01"

    # 4) ollama provider: should construct OllamaEmbeddings and receive base_url from env
    mem_ollama = Memory("ollama", "ollama-model")
    emb_ollama = mem_ollama._embeddings
    assert type(emb_ollama).__name__ == "OllamaEmbeddings"
    assert emb_ollama.model == "ollama-model"
    assert emb_ollama.base_url == "http://ollama.local"


def test_unsupported_provider_round_004():
    """Requesting an unknown provider should raise the expected Exception."""
    # Choose a provider string that doesn't match any case to hit the default branch
    with pytest.raises(Exception) as excinfo:
        Memory("this_provider_does_not_exist", "model-x")
    assert "Embedding not found." in str(excinfo.value)
