# file: gpt_researcher/llm_provider/generic/base.py:121-308
# asked: {"lines": [123, 124, 125, 128, 129, 131, 132, 133, 134, 136, 137, 138, 139, 141, 142, 143, 145, 146, 147, 148, 150, 151, 152, 153, 155, 156, 157, 158, 160, 161, 162, 163, 165, 166, 167, 168, 169, 171, 172, 173, 174, 176, 177, 178, 179, 182, 183, 185, 186, 187, 188, 190, 191, 192, 193, 194, 195, 196, 198, 199, 200, 201, 203, 204, 205, 206, 207, 208, 209, 211, 212, 213, 215, 216, 217, 219, 220, 221, 222, 224, 225, 226, 228, 229, 230, 232, 233, 234, 235, 237, 238, 239, 240, 241, 242, 244, 246, 247, 248, 249, 252, 253, 254, 255, 256, 258, 259, 260, 261, 262, 263, 264, 266, 267, 268, 270, 271, 272, 274, 275, 276, 278, 279, 280, 282, 283, 284, 286, 287, 288, 290, 291, 292, 294, 295, 296, 298, 299, 300, 302, 304, 305, 306, 308], "branches": [[123, 124], [123, 132], [128, 129], [128, 131], [132, 133], [132, 137], [137, 138], [137, 146], [141, 142], [141, 145], [146, 147], [146, 151], [151, 152], [151, 156], [156, 157], [156, 161], [161, 162], [161, 166], [166, 167], [166, 172], [172, 173], [172, 177], [177, 178], [177, 186], [182, 183], [182, 185], [186, 187], [186, 194], [190, 191], [190, 193], [194, 195], [194, 199], [199, 200], [199, 207], [203, 204], [203, 206], [207, 208], [207, 215], [215, 216], [215, 220], [220, 221], [220, 228], [228, 229], [228, 233], [233, 234], [233, 239], [239, 240], [239, 258], [258, 259], [258, 266], [266, 267], [266, 274], [274, 275], [274, 282], [282, 283], [282, 290], [290, 291], [290, 298], [298, 299], [298, 304]]}
# gained: {"lines": [123, 124, 125, 128, 129, 131, 132, 137, 138, 139, 141, 142, 143, 145, 146, 151, 156, 161, 166, 167, 168, 169, 171, 172, 177, 186, 187, 188, 190, 191, 192, 193, 194, 199, 200, 201, 203, 204, 205, 206, 207, 215, 220, 221, 222, 224, 225, 226, 228, 233, 234, 235, 237, 238, 239, 240, 241, 242, 244, 246, 247, 248, 249, 252, 253, 254, 255, 256, 258, 259, 260, 261, 262, 263, 264, 266, 274, 282, 290, 298, 299, 300, 302, 304, 305, 306, 308], "branches": [[123, 124], [123, 132], [128, 129], [132, 137], [137, 138], [137, 146], [141, 142], [146, 151], [151, 156], [156, 161], [161, 166], [166, 167], [166, 172], [172, 177], [177, 186], [186, 187], [186, 194], [190, 191], [194, 199], [199, 200], [199, 207], [203, 204], [207, 215], [215, 220], [220, 221], [220, 228], [228, 233], [233, 234], [233, 239], [239, 240], [239, 258], [258, 259], [258, 266], [266, 274], [274, 282], [282, 290], [290, 298], [298, 299], [298, 304]]}

import importlib
import sys
import types
import os
import pytest

# Helper to create fake modules (including nested) and put them into sys.modules
def create_module(module_name, attrs: dict):
    parts = module_name.split('.')
    for i in range(1, len(parts) + 1):
        mod_name = '.'.join(parts[:i])
        if mod_name not in sys.modules:
            sys.modules[mod_name] = types.ModuleType(mod_name)
        mod = sys.modules[mod_name]
    # Assign attributes on the final module object
    mod = sys.modules[module_name]
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod

# A generic fake LLM class used for most providers; stores received kwargs for assertions
class FakeLLM:
    def __init__(self, **kwargs):
        # copy to avoid mutation issues
        self.received_kwargs = dict(kwargs)

# A fake rate limiter that stores provided arguments
class FakeRateLimiter:
    def __init__(self, requests_per_second=1.0, check_every_n_seconds=None, max_bucket_size=None):
        self.requests_per_second = float(requests_per_second)
        self.check_every_n_seconds = check_every_n_seconds
        self.max_bucket_size = max_bucket_size

# Prepare many fake modules/classes used by GenericLLMProvider.from_provider
@pytest.fixture(autouse=True)
def fake_langchain_modules(monkeypatch):
    # Ensure base module is importable
    base_name = "gpt_researcher.llm_provider.generic.base"
    base_mod = importlib.import_module(base_name)
    # Monkeypatch the internal _check_pkg to a no-op so tests don't require real packages
    monkeypatch.setattr(base_mod, "_check_pkg", lambda pkg: None)

    # Minimal modules and classes required by branches
    # langchain_openai: ChatOpenAI and AzureChatOpenAI
    create_module("langchain_openai", {
        "ChatOpenAI": FakeLLM,
        "AzureChatOpenAI": FakeLLM,
    })

    # langchain_anthropic
    create_module("langchain_anthropic", {"ChatAnthropic": FakeLLM})

    # langchain_cohere
    create_module("langchain_cohere", {"ChatCohere": FakeLLM})

    # google vertex/genai
    create_module("langchain_google_vertexai", {"ChatVertexAI": FakeLLM})
    create_module("langchain_google_genai", {"ChatGoogleGenerativeAI": FakeLLM})

    # fireworks
    create_module("langchain_fireworks", {"ChatFireworks": FakeLLM})

    # ollama needs langchain_community and langchain_ollama
    create_module("langchain_community", {})
    create_module("langchain_ollama", {"ChatOllama": FakeLLM})

    # together
    create_module("langchain_together", {"ChatTogether": FakeLLM})

    # mistralai
    create_module("langchain_mistralai", {"ChatMistralAI": FakeLLM})

    # huggingface
    create_module("langchain_huggingface", {"ChatHuggingFace": FakeLLM})

    # groq
    create_module("langchain_groq", {"ChatGroq": FakeLLM})

    # aws / bedrock
    create_module("langchain_aws", {"ChatBedrock": FakeLLM})

    # xai
    create_module("langchain_xai", {"ChatXAI": FakeLLM})

    # community chat_models.litellm.ChatLiteLLM
    create_module("langchain_community.chat_models.litellm", {"ChatLiteLLM": FakeLLM})
    # gigachat.chat_models.GigaChat
    create_module("langchain_gigachat.chat_models", {"GigaChat": FakeLLM})
    # langchain_netmind
    create_module("langchain_netmind", {"ChatNetmind": FakeLLM})

    # langchain_core.rate_limiters.InMemoryRateLimiter
    create_module("langchain_core.rate_limiters", {"InMemoryRateLimiter": FakeRateLimiter})

    # After setting up, yield to tests
    yield

    # Cleanup: remove modules we added to sys.modules to avoid side effects
    to_remove = [
        "langchain_openai", "langchain_anthropic", "langchain_cohere",
        "langchain_google_vertexai", "langchain_google_genai", "langchain_fireworks",
        "langchain_community", "langchain_ollama", "langchain_together",
        "langchain_mistralai", "langchain_huggingface", "langchain_groq",
        "langchain_aws", "langchain_xai",
        "langchain_community.chat_models.litellm",
        "langchain_gigachat.chat_models",
        "langchain_netmind", "langchain_core.rate_limiters",
    ]
    for m in to_remove:
        sys.modules.pop(m, None)


def test_from_provider_various_branches(monkeypatch, fake_langchain_modules):
    base_name = "gpt_researcher.llm_provider.generic.base"
    base_mod = importlib.import_module(base_name)
    GenericLLMProvider = getattr(base_mod, "GenericLLMProvider")

    # 1) openai: test that OPENAI_BASE_URL environment variable is applied when openai_api_base not provided
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.openai.base")
    provider_obj = GenericLLMProvider.from_provider("openai")
    assert isinstance(provider_obj.llm, FakeLLM)
    # Confirm the fake ChatOpenAI received the openai_api_base from environment
    assert provider_obj.llm.received_kwargs.get("openai_api_base") == "https://example.openai.base"
    # Clean env
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    # 2) azure_openai: when model provided, it becomes azure_deployment
    az = GenericLLMProvider.from_provider("azure_openai", model="azure-model-1")
    assert isinstance(az.llm, FakeLLM)
    assert az.llm.received_kwargs.get("azure_deployment") == "azure-model-1"
    # original model key should still exist per implementation (they did not pop)
    assert az.llm.received_kwargs.get("model") == "azure-model-1"

    # 3) huggingface: model_name -> model_id and original keys removed
    hf = GenericLLMProvider.from_provider("huggingface", model_name="hf-123", extra="x")
    assert isinstance(hf.llm, FakeLLM)
    assert hf.llm.received_kwargs.get("model_id") == "hf-123"
    assert "model_name" not in hf.llm.received_kwargs
    assert "model" not in hf.llm.received_kwargs
    assert hf.llm.received_kwargs.get("extra") == "x"

    # 4) bedrock: model -> model_id and model_kwargs nesting
    bed = GenericLLMProvider.from_provider("bedrock", model="bed-model", foo="bar")
    assert isinstance(bed.llm, FakeLLM)
    assert bed.llm.received_kwargs.get("model_id") == "bed-model"
    assert isinstance(bed.llm.received_kwargs.get("model_kwargs"), dict)
    assert bed.llm.received_kwargs["model_kwargs"].get("foo") == "bar"

    # 5) gigachat: model should be popped (not passed to GigaChat)
    gig = GenericLLMProvider.from_provider("gigachat", model="GigaChat-Max", opt=1)
    assert isinstance(gig.llm, FakeLLM)
    assert "model" not in gig.llm.received_kwargs
    assert gig.llm.received_kwargs.get("opt") == 1

    # 6) openrouter: rate limiter should be created with OPENROUTER_LIMIT_RPS and passed into ChatOpenAI
    monkeypatch.setenv("OPENROUTER_API_KEY", "OR-KEY")
    monkeypatch.setenv("OPENROUTER_LIMIT_RPS", "2.5")
    orp = GenericLLMProvider.from_provider("openrouter", something="yes")
    assert isinstance(orp.llm, FakeLLM)
    # Check the API key was forwarded
    assert orp.llm.received_kwargs.get("openai_api_key") == "OR-KEY"
    # Check rate_limiter was passed and has the expected rps
    rl = orp.llm.received_kwargs.get("rate_limiter")
    assert isinstance(rl, FakeRateLimiter)
    assert rl.requests_per_second == pytest.approx(2.5)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_LIMIT_RPS", raising=False)

    # 7) vllm_openai: use env variables to set keys
    monkeypatch.setenv("VLLM_OPENAI_API_KEY", "VLLM-KEY")
    monkeypatch.setenv("VLLM_OPENAI_API_BASE", "https://vllm.base")
    vllm = GenericLLMProvider.from_provider("vllm_openai")
    assert isinstance(vllm.llm, FakeLLM)
    assert vllm.llm.received_kwargs.get("openai_api_key") == "VLLM-KEY"
    assert vllm.llm.received_kwargs.get("openai_api_base") == "https://vllm.base"
    monkeypatch.delenv("VLLM_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("VLLM_OPENAI_API_BASE", raising=False)

    # 8) ollama: should import ChatOllama and be instantiated using OLLAMA_BASE_URL
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.local")
    oll = GenericLLMProvider.from_provider("ollama", foo="bar")
    assert isinstance(oll.llm, FakeLLM)
    assert oll.llm.received_kwargs.get("base_url") == "http://ollama.local"
    assert oll.llm.received_kwargs.get("foo") == "bar"
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

    # 9) deepseek: should use DEEPSEEK_API_KEY and openai_api_base fixed to deepseek's url
    monkeypatch.setenv("DEEPSEEK_API_KEY", "DS-KEY")
    deep = GenericLLMProvider.from_provider("deepseek", timeout=10)
    assert isinstance(deep.llm, FakeLLM)
    assert deep.llm.received_kwargs.get("openai_api_key") == "DS-KEY"
    assert deep.llm.received_kwargs.get("openai_api_base") == "https://api.deepseek.com"
    assert deep.llm.received_kwargs.get("timeout") == 10
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    # 10) netmind: ensure ChatNetmind is constructed with kwargs
    nm = GenericLLMProvider.from_provider("netmind", special="x")
    assert isinstance(nm.llm, FakeLLM)
    assert nm.llm.received_kwargs.get("special") == "x"


def test_unsupported_provider_raises(monkeypatch, fake_langchain_modules):
    base_name = "gpt_researcher.llm_provider.generic.base"
    base_mod = importlib.import_module(base_name)
    GenericLLMProvider = getattr(base_mod, "GenericLLMProvider")

    # Ensure _SUPPORTED_PROVIDERS exists and is a sequence we can check in the error message
    supported = getattr(base_mod, "_SUPPORTED_PROVIDERS", None)
    assert supported is not None and len(supported) > 0

    with pytest.raises(ValueError) as exc:
        GenericLLMProvider.from_provider("this_provider_does_not_exist")

    # Error message should include the list of supported providers
    msg = str(exc.value)
    for prov in supported:
        assert prov in msg
