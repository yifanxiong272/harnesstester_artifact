import types
import sys
import os
import importlib
import pytest

from gpt_researcher.llm_provider.generic import base


# Helper to inject fake modules into sys.modules deterministically
def make_module(name, attrs=None):
    mod = types.ModuleType(name)
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


class SimpleLLM:
    def __init__(self, **kwargs):
        # record kwargs and promote keys to attributes for easy assertions
        self._init_kwargs = dict(kwargs)
        for k, v in kwargs.items():
            setattr(self, k, v)


class InMemoryRateLimiter:
    def __init__(self, requests_per_second=1.0, check_every_n_seconds=0.1, max_bucket_size=10):
        self.requests_per_second = requests_per_second
        self.check_every_n_seconds = check_every_n_seconds
        self.max_bucket_size = max_bucket_size


@pytest.fixture(autouse=True)
def noop_check_pkg_and_cleanup(monkeypatch):
    # make _check_pkg a no-op to avoid requiring real packages
    monkeypatch.setattr(base, "_check_pkg", lambda pkg: None)
    # ensure we start tests with a clean-ish set of env vars used by the function
    env_backup = {k: os.environ.get(k) for k in [
        "OPENAI_BASE_URL",
        "OLLAMA_BASE_URL",
        "MISTRAL_BASE_URL",
        "OPENROUTER_LIMIT_RPS",
        "OPENROUTER_API_KEY",
        "VLLM_OPENAI_API_KEY",
        "VLLM_OPENAI_API_BASE",
        "DASHSCOPE_API_KEY",
        "DEEPSEEK_API_KEY",
        "AIMLAPI_API_KEY",
        "FORGE_API_KEY",
        "AVIAN_API_KEY",
        "MINIMAX_API_KEY",
    ]}
    try:
        yield
    finally:
        # restore env
        for k, v in env_backup.items():
            if v is None and k in os.environ:
                del os.environ[k]
            elif v is not None:
                os.environ[k] = v


def test_from_provider_openai_round_001(monkeypatch):
    # Cover branch that uses OPENAI_BASE_URL if openai_api_base not provided
    os.environ["OPENAI_BASE_URL"] = "https://custom-openai.example"

    # Provide fake langchain_openai with ChatOpenAI
    make_module("langchain_openai", {"ChatOpenAI": SimpleLLM, "AzureChatOpenAI": SimpleLLM})

    prov = base.GenericLLMProvider.from_provider("openai")
    # ensure returned wrapper contains our fake LLM and that env value was forwarded
    assert hasattr(prov, "llm")
    assert isinstance(prov.llm, SimpleLLM)
    assert getattr(prov.llm, "openai_api_base") == "https://custom-openai.example"


def test_from_provider_azure_model_round_001(monkeypatch):
    # azure_openai branch with model in kwargs should be remapped to azure_deployment
    make_module("langchain_openai", {"AzureChatOpenAI": SimpleLLM})

    prov = base.GenericLLMProvider.from_provider("azure_openai", model="azure-model-x", extra="y")
    assert isinstance(prov.llm, SimpleLLM)
    # Azure branch transforms model -> azure_deployment in kwargs passed to AzureChatOpenAI
    assert getattr(prov.llm, "azure_deployment") == "azure-model-x"
    # ensure other kwargs preserved
    assert getattr(prov.llm, "extra") == "y"


def test_from_provider_ollama_round_001(monkeypatch):
    # ollama branch reads OLLAMA_BASE_URL from env
    os.environ["OLLAMA_BASE_URL"] = "http://ollama.internal"

    make_module("langchain_ollama", {"ChatOllama": SimpleLLM})

    prov = base.GenericLLMProvider.from_provider("ollama", some_kw=123)
    assert isinstance(prov.llm, SimpleLLM)
    # ChatOllama should be invoked with base_url from env
    assert getattr(prov.llm, "base_url") == "http://ollama.internal"
    assert getattr(prov.llm, "some_kw") == 123


def test_from_provider_mistralai_round_001(monkeypatch):
    # mistralai branch sets endpoint from MISTRAL_BASE_URL when endpoint/base_url not provided
    os.environ["MISTRAL_BASE_URL"] = "https://mistral.example/api"
    make_module("langchain_mistralai", {"ChatMistralAI": SimpleLLM})

    prov = base.GenericLLMProvider.from_provider("mistralai")
    assert isinstance(prov.llm, SimpleLLM)
    # Ensure endpoint kw was injected
    assert getattr(prov.llm, "endpoint") == "https://mistral.example/api"


def test_from_provider_huggingface_modelname_round_001(monkeypatch):
    # huggingface branch remaps model or model_name -> model_id
    make_module("langchain_huggingface", {"ChatHuggingFace": SimpleLLM})

    prov = base.GenericLLMProvider.from_provider("huggingface", model_name="hf-model-1", other=5)
    assert isinstance(prov.llm, SimpleLLM)
    # model_name should become model_id passed into initializer
    assert getattr(prov.llm, "model_id") == "hf-model-1"
    assert getattr(prov.llm, "other") == 5


def test_from_provider_bedrock_model_round_001(monkeypatch):
    # bedrock branch wraps model into model_id and model_kwargs
    make_module("langchain_aws", {"ChatBedrock": SimpleLLM})

    prov = base.GenericLLMProvider.from_provider("bedrock", model="bedrock-v1", extra1=1)
    assert isinstance(prov.llm, SimpleLLM)
    # results should include model_id and model_kwargs mapping
    assert getattr(prov.llm, "model_id") == "bedrock-v1"
    # model_kwargs in this fake will be set as an attribute named model_kwargs if passed as kw
    # The implementation builds kwargs = {"model_id": model_id, "model_kwargs": kwargs}
    assert isinstance(getattr(prov.llm, "model_kwargs"), dict)
    assert prov.llm.model_kwargs.get("extra1") == 1


def test_from_provider_openrouter_round_001(monkeypatch):
    # openrouter branch constructs an InMemoryRateLimiter and passes it into ChatOpenAI
    os.environ["OPENROUTER_LIMIT_RPS"] = "2.5"
    os.environ["OPENROUTER_API_KEY"] = "fake-openrouter-key"

    # inject langchain_core.rate_limiters.InMemoryRateLimiter
    rate_mod = make_module("langchain_core.rate_limiters", {"InMemoryRateLimiter": InMemoryRateLimiter})
    # ensure parent package also exists
    core_pkg = make_module("langchain_core", {})
    setattr(core_pkg, "rate_limiters", rate_mod)

    # reuse ChatOpenAI fake
    make_module("langchain_openai", {"ChatOpenAI": SimpleLLM})

    prov = base.GenericLLMProvider.from_provider("openrouter")
    assert isinstance(prov.llm, SimpleLLM)
    # openrouter passes openai_api_base constant
    assert getattr(prov.llm, "openai_api_base") == "https://openrouter.ai/api/v1"
    # check rate_limiter object passed
    rl = getattr(prov.llm, "rate_limiter")
    assert isinstance(rl, InMemoryRateLimiter)
    assert rl.requests_per_second == pytest.approx(2.5)
    # ensure openrouter key forwarded
    assert getattr(prov.llm, "openai_api_key") == "fake-openrouter-key"


def test_from_provider_vllm_openai_round_001(monkeypatch):
    # vllm_openai branch pulls API key and base from env
    os.environ["VLLM_OPENAI_API_KEY"] = "vllm-key"
    os.environ["VLLM_OPENAI_API_BASE"] = "https://vllm.example/base"

    make_module("langchain_openai", {"ChatOpenAI": SimpleLLM})

    prov = base.GenericLLMProvider.from_provider("vllm_openai")
    assert isinstance(prov.llm, SimpleLLM)
    assert getattr(prov.llm, "openai_api_key") == "vllm-key"
    assert getattr(prov.llm, "openai_api_base") == "https://vllm.example/base"


def test_from_provider_unsupported_round_001():
    # unsupported provider should raise ValueError and message should list supported providers
    with pytest.raises(ValueError) as exc:
        base.GenericLLMProvider.from_provider("definitely_not_supported123")
    assert "Supported model providers are" in str(exc.value)
