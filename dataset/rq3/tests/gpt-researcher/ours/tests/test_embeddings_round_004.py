import sys
import types
import os
import importlib
import pytest

from gpt_researcher.memory.embeddings import Memory


def _make_langchain_openai_module():
    """Create a fake langchain_openai module with the minimal embedding classes
    used by Memory.__init__ so the dynamic imports succeed during tests.
    """
    m = types.ModuleType("langchain_openai")

    class OpenAIEmbeddings:
        def __init__(self, model=None, **kwargs):
            # store received args for assertions
            self.model = model
            # expose individual expected kw args as attributes for easy assertions
            for k, v in kwargs.items():
                setattr(self, k, v)
            self._received_kwargs = dict(kwargs)

    class AzureOpenAIEmbeddings:
        def __init__(self, model=None, azure_endpoint=None, openai_api_key=None, openai_api_version=None, **kwargs):
            self.model = model
            self.azure_endpoint = azure_endpoint
            self.openai_api_key = openai_api_key
            self.openai_api_version = openai_api_version
            self._received_kwargs = dict(kwargs)

    m.OpenAIEmbeddings = OpenAIEmbeddings
    m.AzureOpenAIEmbeddings = AzureOpenAIEmbeddings
    return m


def test_openai_base_env_injected_round_004(monkeypatch):
    """
    When OPENAI_BASE_URL is present in the environment and no
    openai_api_base is passed in embedding_kwargs, Memory should inject
    OPENAI_BASE_URL into the kwargs passed to OpenAIEmbeddings.
    """
    fake_mod = _make_langchain_openai_module()
    # ensure the dynamic import inside Memory.__init__ finds our fake module
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_mod)

    # set the env var that should be picked up by the code path
    monkeypatch.setenv("OPENAI_BASE_URL", "https://env-base.example/v1")

    mem = Memory(embedding_provider="openai", model="m-openai")

    # ensure we injected the env var into the constructed embeddings instance
    emb = mem._embeddings
    assert emb is not None
    assert emb.model == "m-openai"
    # the code under test sets openai_api_base in embedding_kwargs when the env var exists
    assert hasattr(emb, "openai_api_base")
    assert emb.openai_api_base == "https://env-base.example/v1"


def test_custom_provider_uses_env_and_defaults_round_004(monkeypatch):
    """
    The 'custom' provider path should call OpenAIEmbeddings with
    openai_api_key from env (or default) and default base URL when
    OPENAI_BASE_URL is not set.
    """
    fake_mod = _make_langchain_openai_module()
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_mod)

    # Provide a custom API key and ensure OPENAI_BASE_URL is not set so default is used
    monkeypatch.setenv("OPENAI_API_KEY", "CUSTOM_KEY_42")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    mem = Memory(embedding_provider="custom", model="m-custom")
    emb = mem._embeddings
    assert emb is not None
    assert emb.model == "m-custom"
    # check that the env-based key was read
    assert hasattr(emb, "openai_api_key")
    assert emb.openai_api_key == "CUSTOM_KEY_42"
    # when OPENAI_BASE_URL not set, a default base URL should be passed
    assert hasattr(emb, "openai_api_base")
    assert emb.openai_api_base == "http://localhost:1234/v1"
    # verify the check_embedding_ctx_length kwarg is passed as False
    assert hasattr(emb, "check_embedding_ctx_length")
    assert emb.check_embedding_ctx_length is False


def test_azure_openai_uses_azure_env_and_openai_version_fallback_round_004(monkeypatch):
    """
    The 'azure_openai' branch should construct AzureOpenAIEmbeddings and
    pick up AZURE_* env vars; if AZURE_OPENAI_API_VERSION is not set it
    should fall back to OPENAI_API_VERSION.
    """
    fake_mod = _make_langchain_openai_module()
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_mod)

    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://azure.example")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "AZ_KEY")
    # don't set AZURE_OPENAI_API_VERSION to force the fallback
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)
    monkeypatch.setenv("OPENAI_API_VERSION", "2023-10-01")

    mem = Memory(embedding_provider="azure_openai", model="m-azure")
    emb = mem._embeddings
    assert emb is not None
    assert emb.model == "m-azure"
    assert emb.azure_endpoint == "https://azure.example"
    assert emb.openai_api_key == "AZ_KEY"
    # should have fallen back to OPENAI_API_VERSION
    assert emb.openai_api_version == "2023-10-01"


def test_unknown_provider_raises_round_004():
    """
    Passing an unsupported provider must raise the explicit Exception
    containing 'Embedding not found.' as implemented in the default branch.
    """
    with pytest.raises(Exception) as excinfo:
        Memory(embedding_provider="definitely-not-a-provider", model="m-x")
    assert "Embedding not found." in str(excinfo.value)
