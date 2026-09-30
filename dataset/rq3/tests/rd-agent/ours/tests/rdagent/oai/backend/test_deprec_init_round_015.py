import types
import builtins
import pytest

from types import SimpleNamespace

import importlib

import rdagent.oai.backend.deprec as deprec

# Ensure deterministic behavior by patching heavy or external dependencies on the module under test.
# Tests instantiate DeprecBackend.__init__ while avoiding real network, ssl side-effects, or parent init.

class DummyOpenAI:
    def __init__(self, **kwargs):
        # record kwargs for assertions
        self.kwargs = kwargs

class DummyAzureOpenAI(DummyOpenAI):
    pass

class DummyLlama:
    @staticmethod
    def build(**kwargs):
        return {"built_with": kwargs}

class DummyChatCompletionsClient:
    def __init__(self, endpoint=None, credential=None):
        self.endpoint = endpoint
        self.credential = credential

class DummyAzureKeyCredential:
    def __init__(self, key):
        self.key = key

class DummyDefaultAzureCredential:
    def __init__(self, **kwargs):
        # capture any kwargs (e.g., managed_identity_client_id)
        self.kwargs = kwargs

def setup_common_monkeypatch(monkeypatch):
    """Patch common symbols used by the constructor to avoid external effects."""
    # Avoid executing parent class __init__
    if hasattr(deprec, "APIBackend"):
        monkeypatch.setattr(deprec.APIBackend, "__init__", lambda self, *a, **k: None)

    # Patch Llama builder (may not exist in module; allow creation)
    monkeypatch.setattr(deprec, "Llama", DummyLlama, raising=False)

    # Patch openai clients (allow creation if absent)
    monkeypatch.setattr(deprec, "openai", SimpleNamespace(OpenAI=DummyOpenAI, AzureOpenAI=DummyAzureOpenAI), raising=False)

    # Patch _get_encoder to deterministic result for else-branch
    monkeypatch.setattr(deprec.DeprecBackend, "_get_encoder", lambda self: "encoder")

    # Patch ChatCompletionsClient and AzureKeyCredential used in deepseek branch
    monkeypatch.setattr(deprec, "ChatCompletionsClient", DummyChatCompletionsClient, raising=False)
    monkeypatch.setattr(deprec, "AzureKeyCredential", DummyAzureKeyCredential, raising=False)

    # Patch DefaultAzureCredential and token provider factory
    monkeypatch.setattr(deprec, "DefaultAzureCredential", DummyDefaultAzureCredential, raising=False)
    monkeypatch.setattr(deprec, "get_bearer_token_provider", lambda cred, scope: ("token_provider_for", cred, scope), raising=False)

    # Provide a simple ssl shim that allows assignment
    class SslShim:
        def __init__(self):
            # functions to be assigned
            self._create_unverified_context = lambda: "unverified"
            self._create_default_https_context = None

    monkeypatch.setattr(deprec, "ssl", SslShim(), raising=False)


def make_llm_settings(**overrides):
    # Provide all attributes expected to be read by __init__; set sensible defaults
    defaults = {
        "use_llama2": False,
        "llama2_ckpt_dir": "/ckpt",
        "llama2_tokenizer_path": "/token",
        "chat_max_tokens": 1024,
        "llams2_max_batch_size": 8,
        "use_gcr_endpoint": False,
        "gcr_endpoint_type": None,
        "llama2_70b_endpoint_key": "k70",
        "llama2_70b_endpoint_deployment": "d70",
        "llama2_70b_endpoint": "e70",
        "llama3_70b_endpoint_key": "k73",
        "llama3_70b_endpoint_deployment": "d73",
        "llama3_70b_endpoint": "e73",
        "phi2_endpoint_key": "kphi2",
        "phi2_endpoint_deployment": "dphi2",
        "phi2_endpoint": "ephi2",
        "phi3_4k_endpoint_key": "kphi34k",
        "phi3_4k_endpoint_deployment": "dphi34k",
        "phi3_4k_endpoint": "ephi34k",
        "phi3_128k_endpoint_key": "kphi3128k",
        "phi3_128k_endpoint_deployment": "dphi3128k",
        "phi3_128k_endpoint": "ephi3128k",
        "gcr_endpoint_temperature": 0.1,
        "gcr_endpoint_top_p": 0.5,
        "gcr_endpoint_do_sample": True,
        "gcr_endpoint_max_token": 1000,
        "chat_model_map": {"a": "b"},
        "chat_model": "cm",
        "chat_use_azure_deepseek": False,
        "chat_azure_deepseek_endpoint": "https://deepseek",
        "chat_azure_deepseek_key": "deepseek-key",
        "chat_stream": False,
        "chat_use_azure": False,
        "embedding_use_azure": False,
        "chat_use_azure_token_provider": False,
        "embedding_use_azure_token_provider": False,
        "managed_identity_client_id": None,
        "chat_openai_api_key": None,
        "openai_api_key": None,
        "embedding_openai_api_key": None,
        "chat_openai_base_url": None,
        "embedding_openai_base_url": None,
        "chat_azure_api_base": "https://azure.chat",
        "chat_azure_api_version": "v1",
        "chat_seed": None,
        "embedding_model": "emb-model",
        "embedding_azure_api_base": None,
        "embedding_azure_api_version": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def instantiate_deprec(monkeypatch, llm_settings):
    """Helper to instantiate DeprecBackend.__init__ safely with provided LLM_SETTINGS"""
    # patch module LLM_SETTINGS
    monkeypatch.setattr(deprec, "LLM_SETTINGS", llm_settings)
    # call __init__ on a fresh instance created without invoking APIBackend
    inst = object.__new__(deprec.DeprecBackend)
    # Run constructor under test
    inst.__init__()
    return inst


def test_llama2_branch_round_015(monkeypatch):
    """When use_llama2 is True, DeprecBackend should build a Llama generator and set encoder to None."""
    setup_common_monkeypatch(monkeypatch)
    llm = make_llm_settings(use_llama2=True)

    inst = instantiate_deprec(monkeypatch, llm)

    # generator should be the dict returned by DummyLlama.build; encoder should be None
    assert isinstance(inst.generator, dict)
    assert inst.generator["built_with"]["ckpt_dir"] == llm.llama2_ckpt_dir
    assert inst.encoder is None
    # flags copied
    assert inst.use_llama2 is True


def test_gcr_endpoint_valid_and_invalid_round_015(monkeypatch):
    """Covers gcr endpoint mapping for a valid type and raises ValueError for invalid type."""
    setup_common_monkeypatch(monkeypatch)

    # 1) Valid mapping: llama3_70b
    llm_valid = make_llm_settings(use_gcr_endpoint=True, gcr_endpoint_type="llama3_70b")
    inst_valid = instantiate_deprec(monkeypatch, llm_valid)

    assert inst_valid.gcr_endpoint_key == llm_valid.llama3_70b_endpoint_key
    assert inst_valid.gcr_endpoint_deployment == llm_valid.llama3_70b_endpoint_deployment
    assert inst_valid.gcr_endpoint == llm_valid.llama3_70b_endpoint
    # headers formed properly
    assert inst_valid.headers["Authorization"] == "Bearer " + llm_valid.llama3_70b_endpoint_key
    assert inst_valid.encoder is None

    # 2) Invalid mapping -> ValueError
    llm_invalid = make_llm_settings(use_gcr_endpoint=True, gcr_endpoint_type="something_unknown")
    monkeypatch.setattr(deprec, "LLM_SETTINGS", llm_invalid)
    inst_invalid = object.__new__(deprec.DeprecBackend)
    with pytest.raises(ValueError) as ei:
        inst_invalid.__init__()
    assert "Invalid gcr_endpoint_type" in str(ei.value)


def test_azure_token_provider_and_clients_round_015(monkeypatch):
    """When chat_use_azure and token provider flags are set, DefaultAzureCredential is invoked and
    token_provider is passed into AzureOpenAI constructors for both chat and embedding clients.
    This also validates managed_identity_client_id propagation to DefaultAzureCredential kwargs.
    """
    setup_common_monkeypatch(monkeypatch)

    # Build settings to trigger azure + token_provider path
    llm = make_llm_settings(
        chat_use_azure=True,
        embedding_use_azure=False,
        chat_use_azure_token_provider=True,
        embedding_use_azure_token_provider=False,
        managed_identity_client_id="managed-id-123",
    )

    # Ensure openai.* in module are the dummy classes that capture kwargs
    dummy_openai = SimpleNamespace(OpenAI=DummyOpenAI, AzureOpenAI=DummyAzureOpenAI)
    monkeypatch.setattr(deprec, "openai", dummy_openai, raising=False)

    inst = instantiate_deprec(monkeypatch, llm)

    # Because chat_use_azure is True, chat_client should be an instance of DummyAzureOpenAI
    assert isinstance(inst.chat_client, DummyAzureOpenAI)
    # The token provider should have been created and passed into the AzureOpenAI constructor
    # Our get_bearer_token_provider returns a tuple starting with 'token_provider_for'
    assert inst.chat_client.kwargs.get("azure_ad_token_provider")[0] == "token_provider_for"

    # Validate that managed_identity_client_id was passed to DefaultAzureCredential
    # We patched DefaultAzureCredential to capture kwargs on init; ensure it received managed id via previously set patch
    # Because our get_bearer_token_provider returns the credential we passed into it as second element, verify that
    token_provider_tuple = inst.chat_client.kwargs.get("azure_ad_token_provider")
    # token_provider_tuple = ("token_provider_for", credential, scope)
    assert token_provider_tuple[1].kwargs.get("managed_identity_client_id") == "managed-id-123"

    # Also ensure encoder was set by our patched _get_encoder
    assert inst.encoder == "encoder"
