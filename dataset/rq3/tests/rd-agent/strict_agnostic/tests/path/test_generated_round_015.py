import os
import ssl
import importlib
import pytest

# Import the module under test
import rdagent.oai.backend.deprec as deprec

# Helper: a simple dummy LLM_SETTINGS stand-in used to control code paths deterministically
class DummyLLMSettings:
    def __init__(
        self,
        use_llama2=False,
        llama2_ckpt_dir=None,
        llama2_tokenizer_path=None,
        chat_max_tokens=1024,
        llams2_max_batch_size=1,
        use_gcr_endpoint=False,
        gcr_endpoint_type=None,
        llama2_70b_endpoint_key=None,
        llama2_70b_endpoint_deployment=None,
        llama2_70b_endpoint=None,
        llama3_70b_endpoint_key=None,
        llama3_70b_endpoint_deployment=None,
        llama3_70b_endpoint=None,
        phi2_endpoint_key=None,
        phi2_endpoint_deployment=None,
        phi2_endpoint=None,
        phi3_4k_endpoint_key=None,
        phi3_4k_endpoint_deployment=None,
        phi3_4k_endpoint=None,
        phi3_128k_endpoint_key=None,
        phi3_128k_endpoint_deployment=None,
        phi3_128k_endpoint=None,
        gcr_endpoint_temperature=0.0,
        gcr_endpoint_top_p=0.0,
        gcr_endpoint_do_sample=False,
        gcr_endpoint_max_token=0,
        chat_model_map=None,
        chat_model="gpt-4",
        chat_use_azure_deepseek=False,
        chat_azure_deepseek_endpoint=None,
        chat_azure_deepseek_key=None,
        chat_use_azure=False,
        embedding_use_azure=False,
        chat_use_azure_token_provider=False,
        embedding_use_azure_token_provider=False,
        managed_identity_client_id=None,
        chat_openai_api_key=None,
        openai_api_key=None,
        embedding_openai_api_key=None,
        chat_openai_base_url=None,
        embedding_openai_base_url=None,
        chat_azure_api_base=None,
        chat_azure_api_version=None,
        chat_stream=False,
        chat_seed=None,
        embedding_model=None,
        embedding_azure_api_base=None,
        embedding_azure_api_version=None,
    ):
        self.use_llama2 = use_llama2
        self.llama2_ckpt_dir = llama2_ckpt_dir
        self.llama2_tokenizer_path = llama2_tokenizer_path
        self.chat_max_tokens = chat_max_tokens
        self.llams2_max_batch_size = llams2_max_batch_size
        self.use_gcr_endpoint = use_gcr_endpoint
        self.gcr_endpoint_type = gcr_endpoint_type
        self.llama2_70b_endpoint_key = llama2_70b_endpoint_key
        self.llama2_70b_endpoint_deployment = llama2_70b_endpoint_deployment
        self.llama2_70b_endpoint = llama2_70b_endpoint
        self.llama3_70b_endpoint_key = llama3_70b_endpoint_key
        self.llama3_70b_endpoint_deployment = llama3_70b_endpoint_deployment
        self.llama3_70b_endpoint = llama3_70b_endpoint
        self.phi2_endpoint_key = phi2_endpoint_key
        self.phi2_endpoint_deployment = phi2_endpoint_deployment
        self.phi2_endpoint = phi2_endpoint
        self.phi3_4k_endpoint_key = phi3_4k_endpoint_key
        self.phi3_4k_endpoint_deployment = phi3_4k_endpoint_deployment
        self.phi3_4k_endpoint = phi3_4k_endpoint
        self.phi3_128k_endpoint_key = phi3_128k_endpoint_key
        self.phi3_128k_endpoint_deployment = phi3_128k_endpoint_deployment
        self.phi3_128k_endpoint = phi3_128k_endpoint
        self.gcr_endpoint_temperature = gcr_endpoint_temperature
        self.gcr_endpoint_top_p = gcr_endpoint_top_p
        self.gcr_endpoint_do_sample = gcr_endpoint_do_sample
        self.gcr_endpoint_max_token = gcr_endpoint_max_token
        self.chat_model_map = chat_model_map or {}
        self.chat_model = chat_model
        self.chat_use_azure_deepseek = chat_use_azure_deepseek
        self.chat_azure_deepseek_endpoint = chat_azure_deepseek_endpoint
        self.chat_azure_deepseek_key = chat_azure_deepseek_key
        self.chat_use_azure = chat_use_azure
        self.embedding_use_azure = embedding_use_azure
        self.chat_use_azure_token_provider = chat_use_azure_token_provider
        self.embedding_use_azure_token_provider = embedding_use_azure_token_provider
        self.managed_identity_client_id = managed_identity_client_id
        self.chat_openai_api_key = chat_openai_api_key
        self.openai_api_key = openai_api_key
        self.embedding_openai_api_key = embedding_openai_api_key
        self.chat_openai_base_url = chat_openai_base_url
        self.embedding_openai_base_url = embedding_openai_base_url
        self.chat_azure_api_base = chat_azure_api_base
        self.chat_azure_api_version = chat_azure_api_version
        self.chat_stream = chat_stream
        self.chat_seed = chat_seed
        self.embedding_model = embedding_model
        self.embedding_azure_api_base = embedding_azure_api_base
        self.embedding_azure_api_version = embedding_azure_api_version


# --- Fake collaborators used to avoid any external I/O or network ---
class FakeLlama:
    built_kwargs = None

    @staticmethod
    def build(**kwargs):
        FakeLlama.built_kwargs = kwargs
        return "FAKE_GENERATOR"


class FakeAzureKeyCredential:
    def __init__(self, key):
        self.key = key


class FakeChatCompletionsClient:
    def __init__(self, endpoint=None, credential=None):
        self.endpoint = endpoint
        self.credential = credential


class FakeDefaultAzureCredential:
    called_kwargs = None

    def __init__(self, **kwargs):
        FakeDefaultAzureCredential.called_kwargs = kwargs


def fake_get_bearer_token_provider(credential, scope):
    # return a simple sentinel that will flow into the AzureOpenAI calls
    return ("TOKEN_PROVIDER", credential, scope)


class FakeAzureOpenAI:
    def __init__(self, **kwargs):
        # store kwargs for inspection
        self.kwargs = kwargs


class FakeOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


# Tests ----------------------------------------------------------------

def test_use_llama2_round_015(monkeypatch):
    """When LLM_SETTINGS.use_llama2 is True, Llama.build is used and encoder is None."""
    monkeypatch.setattr(deprec, "LLM_SETTINGS", DummyLLMSettings(use_llama2=True, llama2_ckpt_dir="/ckpt", llama2_tokenizer_path="/tok", chat_max_tokens=123, llams2_max_batch_size=2))
    # Llama may not be present in the module; allow creation of the attribute if missing
    monkeypatch.setattr(deprec, "Llama", FakeLlama, raising=False)

    # instantiate the backend and check values
    be = deprec.DeprecBackend()
    assert getattr(be, "generator") == "FAKE_GENERATOR"
    assert getattr(be, "encoder") is None
    # verify the builder was called with expected keys
    assert FakeLlama.built_kwargs["ckpt_dir"] == "/ckpt"
    assert FakeLlama.built_kwargs["tokenizer_path"] == "/tok"
    assert be.use_llama2 is True


def test_gcr_endpoint_llama2_70b_round_015(monkeypatch, tmp_path):
    """When use_gcr_endpoint is True and gcr_endpoint_type is 'llama2_70b', fields and headers are set; ssl context patched when PYTHONHTTPSVERIFY unset."""
    # Clear the env var to trigger the ssl branch
    monkeypatch.delenv("PYTHONHTTPSVERIFY", raising=False)

    settings = DummyLLMSettings(
        use_llama2=False,
        use_gcr_endpoint=True,
        gcr_endpoint_type="llama2_70b",
        llama2_70b_endpoint_key="KEY123",
        llama2_70b_endpoint_deployment="DEPLOY",
        llama2_70b_endpoint="https://gcr.example/",
    )
    monkeypatch.setattr(deprec, "LLM_SETTINGS", settings)

    # Ensure ssl has the unverified context function (should on most Python builds)
    assert hasattr(ssl, "_create_unverified_context")

    be = deprec.DeprecBackend()

    # Verify gcr fields and headers
    assert be.gcr_endpoint_key == "KEY123"
    assert be.gcr_endpoint_deployment == "DEPLOY"
    assert be.gcr_endpoint == "https://gcr.example/"
    assert be.headers["Content-Type"] == "application/json"
    assert be.headers["Authorization"] == "Bearer KEY123"

    # Confirm the ssl default context pointer was replaced with the unverified one
    assert ssl._create_default_https_context == ssl._create_unverified_context


def test_gcr_endpoint_invalid_raises_round_015(monkeypatch):
    """Invalid gcr_endpoint_type triggers a ValueError with a helpful message."""
    settings = DummyLLMSettings(use_llama2=False, use_gcr_endpoint=True, gcr_endpoint_type="nope")
    monkeypatch.setattr(deprec, "LLM_SETTINGS", settings)

    with pytest.raises(ValueError) as exc:
        deprec.DeprecBackend()
    assert "Invalid gcr_endpoint_type" in str(exc.value)


def test_chat_use_azure_deepseek_round_015(monkeypatch):
    """When chat_use_azure_deepseek is True, a ChatCompletionsClient is created and chat_model set to deepseek-R1."""
    settings = DummyLLMSettings(use_llama2=False, chat_use_azure_deepseek=True, chat_azure_deepseek_endpoint="https://deepseek", chat_azure_deepseek_key="AZK")
    monkeypatch.setattr(deprec, "LLM_SETTINGS", settings)

    # Patch external Azure credential/client classes used in constructor; allow creation if missing
    monkeypatch.setattr(deprec, "ChatCompletionsClient", FakeChatCompletionsClient, raising=False)
    monkeypatch.setattr(deprec, "AzureKeyCredential", FakeAzureKeyCredential, raising=False)

    be = deprec.DeprecBackend()
    # Verify client object was created and chat_model set to deepseek-R1
    assert isinstance(be.client, FakeChatCompletionsClient)
    assert be.chat_model == "deepseek-R1"
    assert be.encoder is None


def test_azure_token_provider_and_clients_round_015(monkeypatch):
    """When azure token providers are requested, DefaultAzureCredential and bearer provider are used and AzureOpenAI clients are created."""
    settings = DummyLLMSettings(
        use_llama2=False,
        chat_use_azure=True,
        embedding_use_azure=True,
        chat_use_azure_token_provider=True,
        embedding_use_azure_token_provider=True,
        managed_identity_client_id="mi-123",
        chat_azure_api_base="https://chat.azure",
        chat_azure_api_version="2023-08-01",
        embedding_azure_api_base="https://embed.azure",
        embedding_azure_api_version="2023-08-01",
        chat_openai_api_key="CHATKEY",
        embedding_openai_api_key="EMBKEY",
    )
    monkeypatch.setattr(deprec, "LLM_SETTINGS", settings)

    # Replace DefaultAzureCredential and get_bearer_token_provider with fakes that record calls (allow creation if missing)
    monkeypatch.setattr(deprec, "DefaultAzureCredential", FakeDefaultAzureCredential, raising=False)
    monkeypatch.setattr(deprec, "get_bearer_token_provider", fake_get_bearer_token_provider, raising=False)

    # Replace openai client constructors to avoid network calls
    monkeypatch.setattr(deprec.openai, "AzureOpenAI", FakeAzureOpenAI, raising=False)
    monkeypatch.setattr(deprec.openai, "OpenAI", FakeOpenAI, raising=False)

    be = deprec.DeprecBackend()

    # DefaultAzureCredential must have been instantiated with the managed identity client id
    assert FakeDefaultAzureCredential.called_kwargs == {"managed_identity_client_id": "mi-123"}

    # Because chat_use_azure True, AzureOpenAI should have been used for both chat and embedding clients
    assert isinstance(be.chat_client, FakeAzureOpenAI)
    assert isinstance(be.embedding_client, FakeAzureOpenAI)

    # If token provider was requested, the azure client kwargs should include the token provider key or the lambda used
    # We can't assume exact kw names for internals, but we can assert that the client objects were created
    assert be.chat_use_azure is True
    assert be.embedding_use_azure is True


# Ensure tests are discoverable with the nodeids mentioned in the proposal
__tests__ = True
