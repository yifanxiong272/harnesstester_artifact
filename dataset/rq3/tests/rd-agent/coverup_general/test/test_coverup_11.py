# file: rdagent/oai/backend/deprec.py:109-236
# asked: {"lines": [114, 115, 116, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 146, 147, 148, 149, 150, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 164, 166, 167, 168, 169, 171, 172, 173, 174, 175, 179, 180, 182, 183, 186, 187, 188, 189, 190, 191, 192, 193, 194, 196, 197, 198, 200, 201, 203, 204, 205, 206, 207, 208, 209, 211, 212, 213, 214, 215, 216, 218, 219, 222, 223, 224, 225, 226, 227, 229, 230, 234, 235, 236], "branches": [[115, 116], [115, 123], [123, 124], [123, 161], [125, 126], [125, 129], [129, 130], [129, 133], [133, 134], [133, 137], [137, 138], [137, 141], [141, 142], [141, 146], [156, 157], [156, 158], [161, 162], [161, 171], [200, 203], [200, 211], [204, 205], [204, 206]]}
# gained: {"lines": [114, 115, 116, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 146, 147, 148, 149, 150, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 164, 166, 167, 168, 169, 171, 172, 173, 174, 175, 179, 180, 182, 183, 186, 187, 188, 189, 190, 191, 192, 193, 194, 196, 197, 198, 200, 201, 203, 204, 205, 206, 207, 208, 209, 211, 212, 213, 214, 215, 216, 218, 222, 223, 224, 225, 226, 227, 229, 234, 235, 236], "branches": [[115, 116], [115, 123], [123, 124], [123, 161], [125, 126], [125, 129], [129, 130], [129, 133], [133, 134], [133, 137], [137, 138], [137, 141], [141, 142], [141, 146], [156, 157], [161, 162], [161, 171], [200, 203], [204, 205]]}

import os
import ssl
import types
import pytest

import rdagent.oai.backend.deprec as deprec_mod
from rdagent.oai.backend.deprec import DeprecBackend
from rdagent.oai.llm_conf import LLM_SETTINGS


class DummyLlama:
    @staticmethod
    def build(**kwargs):
        # return a marker object to verify it was used
        return {"built_with": kwargs}


class DummyChatClient:
    def __init__(self, endpoint=None, credential=None):
        self.endpoint = endpoint
        self.credential = credential


class DummyAzureKeyCredential:
    def __init__(self, key):
        self.key = key


class DummyDefaultAzureCredential:
    def __init__(self, **kwargs):
        # store passed kwargs for assertions
        self.kwargs = kwargs


def dummy_get_bearer_token_provider(cred, scope):
    return {"cred": cred, "scope": scope}


class DummyAzureOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class DummyOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture(autouse=True)
def reset_settings(monkeypatch):
    """
    Ensure default safe values for LLM_SETTINGS and patch external heavy dependencies.
    Each test will override what it needs via monkeypatch.setattr on LLM_SETTINGS.
    """
    # Provide defaults that make the else branch safe
    defaults = dict(
        use_llama2=False,
        use_gcr_endpoint=False,
        gcr_endpoint_type="llama2_70b",
        llama2_ckpt_dir="/tmp",
        llama2_tokenizer_path="/tmp/tokenizer",
        chat_max_tokens=1024,
        llams2_max_batch_size=1,
        llama2_70b_endpoint_key="k70",
        llama2_70b_endpoint_deployment="d70",
        llama2_70b_endpoint="e70",
        llama3_70b_endpoint_key="k73",
        llama3_70b_endpoint_deployment="d73",
        llama3_70b_endpoint="e73",
        phi2_endpoint_key="kphi2",
        phi2_endpoint_deployment="dphi2",
        phi2_endpoint="ephi2",
        phi3_4k_endpoint_key="kphi3_4k",
        phi3_4k_endpoint_deployment="dphi3_4k",
        phi3_4k_endpoint="ephi3_4k",
        phi3_128k_endpoint_key="kphi3_128k",
        phi3_128k_endpoint_deployment="dphi3_128k",
        phi3_128k_endpoint="ephi3_128k",
        gcr_endpoint_temperature=0.1,
        gcr_endpoint_top_p=0.2,
        gcr_endpoint_do_sample=False,
        gcr_endpoint_max_token=512,
        chat_model_map={"a": "b"},
        chat_model="chat-model",
        chat_use_azure_deepseek=False,
        chat_azure_deepseek_endpoint="https://deepseek",
        chat_azure_deepseek_key="deepseek-key",
        chat_stream=False,
        chat_use_azure=False,
        embedding_use_azure=False,
        chat_use_azure_token_provider=False,
        embedding_use_azure_token_provider=False,
        managed_identity_client_id=None,
        chat_openai_api_key=None,
        embedding_openai_api_key=None,
        openai_api_key=None,
        chat_openai_base_url="https://api.openai.example",
        embedding_openai_base_url="https://api.openai.embedding",
        chat_azure_api_base="https://azure.chat",
        chat_azure_api_version="2023-10-01",
        chat_seed=None,
        embedding_model="embed-model",
        embedding_azure_api_base="https://azure.embed",
        embedding_azure_api_version="2023-10-01",
    )
    # Apply defaults to LLM_SETTINGS attributes
    for k, v in defaults.items():
        monkeypatch.setattr(LLM_SETTINGS, k, v, raising=False)

    # Patch heavy external dependencies with safe dummies
    monkeypatch.setattr(deprec_mod, "Llama", DummyLlama, raising=False)
    monkeypatch.setattr(deprec_mod, "ChatCompletionsClient", DummyChatClient, raising=False)
    monkeypatch.setattr(deprec_mod, "AzureKeyCredential", DummyAzureKeyCredential, raising=False)
    monkeypatch.setattr(deprec_mod, "DefaultAzureCredential", DummyDefaultAzureCredential, raising=False)
    monkeypatch.setattr(deprec_mod, "get_bearer_token_provider", dummy_get_bearer_token_provider, raising=False)
    # Patch openai clients
    monkeypatch.setattr(deprec_mod.openai, "AzureOpenAI", DummyAzureOpenAI, raising=False)
    monkeypatch.setattr(deprec_mod.openai, "OpenAI", DummyOpenAI, raising=False)

    # Ensure ssl modifications won't break tests; allow assigning default https context
    # but keep original to restore
    original_create_default = getattr(ssl, "_create_default_https_context", None)
    original_unverified = getattr(ssl, "_create_unverified_context", None)
    try:
        yield
    finally:
        # restore ssl attributes if modified
        if original_create_default is not None:
            ssl._create_default_https_context = original_create_default
        elif hasattr(ssl, "_create_default_https_context"):
            # remove if added by code
            try:
                delattr(ssl, "_create_default_https_context")
            except Exception:
                pass
        if original_unverified is not None:
            ssl._create_unverified_context = original_unverified


def test_use_llama2_branch(monkeypatch):
    # enable llama2 path
    monkeypatch.setattr(LLM_SETTINGS, "use_llama2", True)
    # Prepare specific settings used by constructor
    monkeypatch.setattr(LLM_SETTINGS, "llama2_ckpt_dir", "/ckpt", raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "llama2_tokenizer_path", "/tok", raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "chat_max_tokens", 2048, raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "llams2_max_batch_size", 8, raising=False)

    # Llama.build is already patched to DummyLlama in fixture; create instance
    inst = DeprecBackend()

    # Confirm generator built and encoder set to None
    assert isinstance(inst.generator, dict)
    assert inst.generator["built_with"]["ckpt_dir"] == "/ckpt"
    assert inst.encoder is None

    # check config transfer at the end
    assert inst.use_llama2 is True
    assert inst.use_gcr_endpoint is False
    assert inst.chat_use_azure_deepseek is False


@pytest.mark.parametrize("gcr_type, key_attr, expected_key", [
    ("llama2_70b", "llama2_70b_endpoint_key", "k70"),
    ("llama3_70b", "llama3_70b_endpoint_key", "k73"),
    ("phi2", "phi2_endpoint_key", "kphi2"),
    ("phi3_4k", "phi3_4k_endpoint_key", "kphi3_4k"),
    ("phi3_128k", "phi3_128k_endpoint_key", "kphi3_128k"),
])
def test_gcr_endpoint_types(monkeypatch, gcr_type, key_attr, expected_key):
    # ensure llama2 branch disabled
    monkeypatch.setattr(LLM_SETTINGS, "use_llama2", False, raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "use_gcr_endpoint", True, raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "gcr_endpoint_type", gcr_type, raising=False)

    # Ensure environment var isn't set so the ssl branch triggers (safe due to fixture)
    monkeypatch.delenv("PYTHONHTTPSVERIFY", raising=False)

    inst = DeprecBackend()

    assert inst.gcr_endpoint_key == expected_key
    assert inst.headers["Content-Type"] == "application/json"
    assert inst.encoder is None
    # final flags
    assert inst.use_gcr_endpoint is True


def test_invalid_gcr_endpoint_type_raises(monkeypatch):
    monkeypatch.setattr(LLM_SETTINGS, "use_llama2", False, raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "use_gcr_endpoint", True, raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "gcr_endpoint_type", "not-a-valid-type", raising=False)

    with pytest.raises(ValueError) as ei:
        DeprecBackend()
    assert "Invalid gcr_endpoint_type" in str(ei.value)


def test_chat_use_azure_deepseek_branch(monkeypatch):
    # enable deepseek branch
    monkeypatch.setattr(LLM_SETTINGS, "use_llama2", False, raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "use_gcr_endpoint", False, raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "chat_use_azure_deepseek", True, raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "chat_azure_deepseek_endpoint", "https://deepseek.example", raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "chat_azure_deepseek_key", "ds-key", raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "chat_stream", True, raising=False)

    # Patch AzureKeyCredential to our dummy which stores the key
    monkeypatch.setattr(deprec_mod, "AzureKeyCredential", DummyAzureKeyCredential, raising=False)
    # Patch ChatCompletionsClient to record args; already patched by fixture

    inst = DeprecBackend()

    # client should have been constructed with endpoint and credential carrying the key
    assert isinstance(inst.client, DummyChatClient)
    assert inst.client.endpoint == "https://deepseek.example"
    assert isinstance(inst.client.credential, DummyAzureKeyCredential)
    assert inst.client.credential.key == "ds-key"
    assert inst.chat_model == "deepseek-R1"
    assert inst.chat_stream is True
    assert inst.encoder is None
    assert inst.chat_use_azure_deepseek is True


def test_else_branch_with_azure_token_provider(monkeypatch):
    # disable other branches to reach the else branch
    monkeypatch.setattr(LLM_SETTINGS, "use_llama2", False, raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "use_gcr_endpoint", False, raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "chat_use_azure_deepseek", False, raising=False)

    # ensure azure usage flags are enabled and token provider requested
    monkeypatch.setattr(LLM_SETTINGS, "chat_use_azure", True, raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "embedding_use_azure", True, raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "chat_use_azure_token_provider", True, raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "embedding_use_azure_token_provider", True, raising=False)
    # ensure managed identity client id triggers dac_kwargs branch
    monkeypatch.setattr(LLM_SETTINGS, "managed_identity_client_id", "managed-id-123", raising=False)

    # Provide api keys as well (they should be ignored when token provider is used)
    monkeypatch.setattr(LLM_SETTINGS, "chat_openai_api_key", "chat-key", raising=False)
    monkeypatch.setattr(LLM_SETTINGS, "embedding_openai_api_key", "embed-key", raising=False)

    # patch DeprecBackend._get_encoder to avoid tiktoken dependency
    monkeypatch.setattr(DeprecBackend, "_get_encoder", lambda self: "dummy-encoder", raising=False)

    # Patch DefaultAzureCredential and get_bearer_token_provider to our dummies
    monkeypatch.setattr(deprec_mod, "DefaultAzureCredential", DummyDefaultAzureCredential, raising=False)
    monkeypatch.setattr(deprec_mod, "get_bearer_token_provider", dummy_get_bearer_token_provider, raising=False)

    # openai.AzureOpenAI / OpenAI patched in fixture to DummyAzureOpenAI / DummyOpenAI

    inst = DeprecBackend()

    # encoder should be the dummy
    assert inst.encoder == "dummy-encoder"

    # chat_client should be DummyAzureOpenAI because chat_use_azure is True
    assert isinstance(inst.chat_client, DummyAzureOpenAI)
    # Because token provider is enabled chat_client kwargs should include azure_ad_token_provider and no api_key
    assert "azure_ad_token_provider" in inst.chat_client.kwargs
    assert inst.chat_client.kwargs["azure_ad_token_provider"]["scope"] == "https://cognitiveservices.azure.com/.default"
    assert inst.chat_client.kwargs.get("api_key") is None

    # embedding client similar
    assert isinstance(inst.embedding_client, DummyAzureOpenAI)
    assert "azure_ad_token_provider" in inst.embedding_client.kwargs
    assert inst.embedding_client.kwargs.get("api_key") is None

    # final flags transferred
    assert inst.use_llama2 is False
    assert inst.use_gcr_endpoint is False
    assert inst.chat_use_azure_deepseek is False
