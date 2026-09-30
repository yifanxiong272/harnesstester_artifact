# file: gpt_researcher/llm_provider/generic/base.py:121-308
# asked: {"lines": [123, 124, 125, 128, 129, 131, 132, 133, 134, 136, 137, 138, 139, 141, 142, 143, 145, 146, 147, 148, 150, 151, 152, 153, 155, 156, 157, 158, 160, 161, 162, 163, 165, 166, 167, 168, 169, 171, 172, 173, 174, 176, 177, 178, 179, 182, 183, 185, 186, 187, 188, 190, 191, 192, 193, 194, 195, 196, 198, 199, 200, 201, 203, 204, 205, 206, 207, 208, 209, 211, 212, 213, 215, 216, 217, 219, 220, 221, 222, 224, 225, 226, 228, 229, 230, 232, 233, 234, 235, 237, 238, 239, 240, 241, 242, 244, 246, 247, 248, 249, 252, 253, 254, 255, 256, 258, 259, 260, 261, 262, 263, 264, 266, 267, 268, 270, 271, 272, 274, 275, 276, 278, 279, 280, 282, 283, 284, 286, 287, 288, 290, 291, 292, 294, 295, 296, 298, 299, 300, 302, 304, 305, 306, 308], "branches": [[123, 124], [123, 132], [128, 129], [128, 131], [132, 133], [132, 137], [137, 138], [137, 146], [141, 142], [141, 145], [146, 147], [146, 151], [151, 152], [151, 156], [156, 157], [156, 161], [161, 162], [161, 166], [166, 167], [166, 172], [172, 173], [172, 177], [177, 178], [177, 186], [182, 183], [182, 185], [186, 187], [186, 194], [190, 191], [190, 193], [194, 195], [194, 199], [199, 200], [199, 207], [203, 204], [203, 206], [207, 208], [207, 215], [215, 216], [215, 220], [220, 221], [220, 228], [228, 229], [228, 233], [233, 234], [233, 239], [239, 240], [239, 258], [258, 259], [258, 266], [266, 267], [266, 274], [274, 275], [274, 282], [282, 283], [282, 290], [290, 291], [290, 298], [298, 299], [298, 304]]}
# gained: {"lines": [123, 124, 125, 128, 129, 131, 132, 133, 134, 136, 137, 138, 139, 141, 142, 143, 145, 146, 147, 148, 150, 151, 152, 153, 155, 156, 157, 158, 160, 161, 162, 163, 165, 166, 167, 168, 169, 171, 172, 173, 174, 176, 177, 178, 179, 182, 183, 185, 186, 187, 188, 190, 191, 192, 193, 194, 195, 196, 198, 199, 200, 201, 203, 204, 205, 206, 207, 208, 209, 211, 212, 213, 215, 216, 217, 219, 220, 221, 222, 224, 225, 226, 228, 229, 230, 232, 233, 234, 235, 237, 238, 239, 240, 241, 242, 244, 246, 247, 248, 249, 252, 253, 254, 255, 256, 258, 259, 260, 261, 262, 263, 264, 266, 267, 268, 270, 271, 272, 274, 275, 276, 278, 279, 280, 282, 283, 284, 286, 287, 288, 290, 291, 292, 294, 295, 296, 298, 299, 300, 302, 304, 305, 306, 308], "branches": [[123, 124], [123, 132], [128, 129], [132, 133], [132, 137], [137, 138], [137, 146], [141, 142], [146, 147], [146, 151], [151, 152], [151, 156], [156, 157], [156, 161], [161, 162], [161, 166], [166, 167], [166, 172], [172, 173], [172, 177], [177, 178], [177, 186], [182, 183], [186, 187], [186, 194], [190, 191], [194, 195], [194, 199], [199, 200], [199, 207], [203, 204], [207, 208], [207, 215], [215, 216], [215, 220], [220, 221], [220, 228], [228, 229], [228, 233], [233, 234], [233, 239], [239, 240], [239, 258], [258, 259], [258, 266], [266, 267], [266, 274], [274, 275], [274, 282], [282, 283], [282, 290], [290, 291], [290, 298], [298, 299], [298, 304]]}

import importlib
import sys
import types
import os
import pytest

# Try importing the target module with possible package path variations
try:
    base_mod = importlib.import_module("gpt_researcher.llm_provider.generic.base")
except Exception:
    base_mod = importlib.import_module("gpt_researcher.gpt_researcher.llm_provider.generic.base")

GenericLLMProvider = base_mod.GenericLLMProvider

class FakeLLM:
    def __init__(self, **kwargs):
        self.init_kwargs = kwargs

class FakeRateLimiter:
    def __init__(self, requests_per_second=1.0, check_every_n_seconds=None, max_bucket_size=None):
        self.requests_per_second = requests_per_second
        self.check_every_n_seconds = check_every_n_seconds
        self.max_bucket_size = max_bucket_size

def _make_module(name, attrs: dict):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    return m

@pytest.fixture(autouse=True)
def setup_fake_langchain_modules(monkeypatch):
    """
    Create fake modules and monkeypatch base_mod._check_pkg to no-op.
    This fixture is autouse so every test uses these fakes and they are cleaned up.
    """
    # Common top-level modules mapping to simple classes
    simple_map = {
        "langchain_openai": {"ChatOpenAI": FakeLLM, "AzureChatOpenAI": FakeLLM},
        "langchain_anthropic": {"ChatAnthropic": FakeLLM},
        "langchain_cohere": {"ChatCohere": FakeLLM},
        "langchain_google_vertexai": {"ChatVertexAI": FakeLLM},
        "langchain_google_genai": {"ChatGoogleGenerativeAI": FakeLLM},
        "langchain_fireworks": {"ChatFireworks": FakeLLM},
        "langchain_ollama": {"ChatOllama": FakeLLM},
        "langchain_together": {"ChatTogether": FakeLLM},
        "langchain_mistralai": {"ChatMistralAI": FakeLLM},
        "langchain_huggingface": {"ChatHuggingFace": FakeLLM},
        "langchain_groq": {"ChatGroq": FakeLLM},
        "langchain_aws": {"ChatBedrock": FakeLLM},
        "langchain_xai": {"ChatXAI": FakeLLM},
        "langchain_gigachat": {},
        "langchain_netmind": {"ChatNetmind": FakeLLM},
    }

    # Insert simple modules
    for mod_name, attrs in simple_map.items():
        mod = _make_module(mod_name, attrs)
        monkeypatch.setitem(sys.modules, mod_name, mod)

    # langchain_community.chat_models.litellm -> ChatLiteLLM
    litellm_mod = _make_module("langchain_community.chat_models.litellm", {"ChatLiteLLM": FakeLLM})
    monkeypatch.setitem(sys.modules, "langchain_community.chat_models.litellm", litellm_mod)

    # langchain_gigachat.chat_models -> GigaChat
    gigachat_mod = _make_module("langchain_gigachat.chat_models", {"GigaChat": FakeLLM})
    monkeypatch.setitem(sys.modules, "langchain_gigachat.chat_models", gigachat_mod)

    # langchain_core.rate_limiters -> InMemoryRateLimiter
    rate_mod = _make_module("langchain_core.rate_limiters", {"InMemoryRateLimiter": FakeRateLimiter})
    monkeypatch.setitem(sys.modules, "langchain_core.rate_limiters", rate_mod)

    # Ensure top-level langchain_gigachat exists (some imports reference package directly)
    monkeypatch.setitem(sys.modules, "langchain_gigachat", types.ModuleType("langchain_gigachat"))

    # Provide langchain_community package too
    monkeypatch.setitem(sys.modules, "langchain_community", types.ModuleType("langchain_community"))

    # Monkeypatch the module's _check_pkg to a no-op so provider checks pass
    monkeypatch.setattr(base_mod, "_check_pkg", lambda pkg: None)

    yield  # test runs

def test_from_provider_various(monkeypatch):
    # Set environment variables required by specific branches
    env = {
        "OPENAI_BASE_URL": "https://openai.custom",
        "OLLAMA_BASE_URL": "https://ollama.local",
        "MISTRAL_BASE_URL": "https://mistral.local",
        "DASHSCOPE_API_KEY": "dashkey123",
        "DEEPSEEK_API_KEY": "deepkey456",
        "OPENROUTER_API_KEY": "orkey789",
        "OPENROUTER_LIMIT_RPS": "2.5",
        "VLLM_OPENAI_API_KEY": "vllmkey",
        "VLLM_OPENAI_API_BASE": "https://vllm.base",
        "AIMLAPI_API_KEY": "aimlkey",
        "FORGE_API_KEY": "forgekey",
        "AVIAN_API_KEY": "aviankey",
        "MINIMAX_API_KEY": "minimaxkey",
        # GIGACHAT_MODEL not strictly required, but ensure no surprises
        "GIGACHAT_MODEL": "GigaChat-Max",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    # Providers to test with optional special kwargs for assertion
    providers_to_test = [
        ("openai", {}, "ChatOpenAI", lambda llm: llm.init_kwargs.get("openai_api_base") == env["OPENAI_BASE_URL"]),
        ("anthropic", {}, "ChatAnthropic", lambda llm: True),
        ("azure_openai", {"model": "azure-model-1"}, "AzureChatOpenAI", lambda llm: llm.init_kwargs.get("azure_deployment") == "azure-model-1"),
        ("cohere", {}, "ChatCohere", lambda llm: True),
        ("google_vertexai", {}, "ChatVertexAI", lambda llm: True),
        ("google_genai", {}, "ChatGoogleGenerativeAI", lambda llm: True),
        ("fireworks", {}, "ChatFireworks", lambda llm: True),
        ("ollama", {}, "ChatOllama", lambda llm: llm.init_kwargs.get("base_url") == env["OLLAMA_BASE_URL"]),
        ("together", {}, "ChatTogether", lambda llm: True),
        ("mistralai", {}, "ChatMistralAI", lambda llm: llm.init_kwargs.get("endpoint") == env["MISTRAL_BASE_URL"]),
        ("huggingface", {"model": "hf-model"}, "ChatHuggingFace", lambda llm: llm.init_kwargs.get("model_id") == "hf-model"),
        ("groq", {}, "ChatGroq", lambda llm: True),
        ("bedrock", {"model": "bedrock-1", "extra": "val"}, "ChatBedrock", lambda llm: llm.init_kwargs.get("model_id") == "bedrock-1" and isinstance(llm.init_kwargs.get("model_kwargs"), dict) and llm.init_kwargs["model_kwargs"].get("extra") == "val"),
        ("dashscope", {}, "ChatOpenAI", lambda llm: llm.init_kwargs.get("openai_api_base", "").startswith("https://dashscope.aliyuncs.com") and llm.init_kwargs.get("openai_api_key") == env["DASHSCOPE_API_KEY"]),
        ("xai", {}, "ChatXAI", lambda llm: True),
        ("deepseek", {}, "ChatOpenAI", lambda llm: llm.init_kwargs.get("openai_api_base", "") == "https://api.deepseek.com" and llm.init_kwargs.get("openai_api_key") == env["DEEPSEEK_API_KEY"]),
        ("litellm", {}, "ChatLiteLLM", lambda llm: True),
        ("gigachat", {"model": "should-be-popped"}, "GigaChat", lambda llm: "model" not in llm.init_kwargs),
        ("openrouter", {}, "ChatOpenAI", lambda llm: llm.init_kwargs.get("openai_api_key") == env["OPENROUTER_API_KEY"] and hasattr(llm.init_kwargs.get("rate_limiter"), "requests_per_second")),
        ("vllm_openai", {}, "ChatOpenAI", lambda llm: llm.init_kwargs.get("openai_api_key") == env["VLLM_OPENAI_API_KEY"] and llm.init_kwargs.get("openai_api_base") == env["VLLM_OPENAI_API_BASE"]),
        ("aimlapi", {}, "ChatOpenAI", lambda llm: llm.init_kwargs.get("openai_api_key") == env["AIMLAPI_API_KEY"] and llm.init_kwargs.get("openai_api_base", "").startswith("https://api.aimlapi.com")),
        ("forge", {}, "ChatOpenAI", lambda llm: llm.init_kwargs.get("openai_api_key") == env["FORGE_API_KEY"] and llm.init_kwargs.get("openai_api_base", "").startswith("https://api.forge.tensorblock.co")),
        ("avian", {}, "ChatOpenAI", lambda llm: llm.init_kwargs.get("openai_api_key") == env["AVIAN_API_KEY"] and llm.init_kwargs.get("openai_api_base", "").startswith("https://api.avian.io")),
        ("minimax", {}, "ChatOpenAI", lambda llm: llm.init_kwargs.get("openai_api_key") == env["MINIMAX_API_KEY"] and llm.init_kwargs.get("openai_api_base", "").startswith("https://api.minimax.io")),
        ("netmind", {}, "ChatNetmind", lambda llm: True),
    ]

    for provider, kwargs, _clsname, cond in providers_to_test:
        # Call without chat_log (None) to avoid ChatLogger dependency in __init__
        inst = GenericLLMProvider.from_provider(provider, **kwargs)
        assert isinstance(inst, GenericLLMProvider)
        # The created llm should be our FakeLLM (or for rate-limiter case, still FakeLLM)
        llm = inst.llm
        assert hasattr(llm, "init_kwargs")
        assert cond(llm), f"Condition failed for provider {provider}; init_kwargs={llm.init_kwargs}"

def test_from_provider_unsupported_raises(monkeypatch):
    # Ensure _check_pkg no-op
    monkeypatch.setattr(base_mod, "_check_pkg", lambda pkg: None)

    # Build the expected supported string from the module variable
    supported = ", ".join(getattr(base_mod, "_SUPPORTED_PROVIDERS"))
    bad_provider = "this_provider_does_not_exist"

    with pytest.raises(ValueError) as ei:
        GenericLLMProvider.from_provider(bad_provider)

    msg = str(ei.value)
    assert "Unsupported this_provider_does_not_exist" in msg or "Unsupported" in msg
    assert supported in msg
