import types
import sys
import os
import pytest

from gpt_researcher.llm_provider.generic import base
from gpt_researcher.llm_provider.generic.base import GenericLLMProvider

# Helper factories to inject fake langchain modules that capture kwargs passed to constructors

def _inject_langchain_openai_module():
    m = types.ModuleType('langchain_openai')
    class ChatOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
    class AzureChatOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
    m.ChatOpenAI = ChatOpenAI
    m.AzureChatOpenAI = AzureChatOpenAI
    return m


def _inject_langchain_huggingface_module():
    m = types.ModuleType('langchain_huggingface')
    class ChatHuggingFace:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
    m.ChatHuggingFace = ChatHuggingFace
    return m


def _inject_langchain_aws_module():
    m = types.ModuleType('langchain_aws')
    class ChatBedrock:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
    m.ChatBedrock = ChatBedrock
    return m


def _inject_langchain_core_rate_limiters():
    # We need both the top-level package and the submodule name present in sys.modules
    pkg = types.ModuleType('langchain_core')
    sub = types.ModuleType('langchain_core.rate_limiters')
    class InMemoryRateLimiter:
        def __init__(self, requests_per_second=1.0, check_every_n_seconds=0.1, max_bucket_size=10):
            self.requests_per_second = float(requests_per_second)
            self.check_every_n_seconds = check_every_n_seconds
            self.max_bucket_size = max_bucket_size
        def __repr__(self):
            return f'InMemoryRateLimiter(rps={self.requests_per_second})'
    sub.InMemoryRateLimiter = InMemoryRateLimiter
    return pkg, sub


@pytest.fixture(autouse=True)
def noop_check_pkg(monkeypatch):
    # Prevent the real _check_pkg from trying to import/inspect real optional packages
    monkeypatch.setattr(base, '_check_pkg', lambda pkg: None)


def test_openai_round_001(monkeypatch):
    """Cover the openai branch and OPENAI_BASE_URL handling (lines ~123-131)."""
    fake_openai = _inject_langchain_openai_module()
    monkeypatch.setitem(sys.modules, 'langchain_openai', fake_openai)

    # Ensure the environment path is used when openai_api_base not provided in kwargs
    monkeypatch.setenv('OPENAI_BASE_URL', 'https://example.base/')

    provider = GenericLLMProvider.from_provider('openai', chat_log=None, verbose=False)

    # The returned provider should wrap our fake ChatOpenAI instance
    assert hasattr(provider, 'llm')
    llm = provider.llm
    assert isinstance(llm, fake_openai.ChatOpenAI)
    # The environment-provided base URL should have been injected into kwargs
    assert llm.kwargs.get('openai_api_base') == 'https://example.base/'
    # Verbose flag should be passed through to constructor return value wrapper (class returns provider)
    assert provider.verbose is False


def test_azure_round_001(monkeypatch):
    """Cover azure_openai branch and the model->azure_deployment transformation (lines ~137-145)."""
    fake_openai = _inject_langchain_openai_module()
    monkeypatch.setitem(sys.modules, 'langchain_openai', fake_openai)

    provider = GenericLLMProvider.from_provider('azure_openai', chat_log='log', verbose=True, model='deployment-123', extra='x')

    assert hasattr(provider, 'llm')
    llm = provider.llm
    # AzureChatOpenAI should have been instantiated
    assert isinstance(llm, fake_openai.AzureChatOpenAI)
    # Ensure that azure_deployment key was inserted
    assert llm.kwargs.get('azure_deployment') == 'deployment-123'
    # Original model key should still be present in the kwargs passed (because of how dict unpacking is done)
    assert 'model' in llm.kwargs


def test_huggingface_round_001(monkeypatch):
    """Cover huggingface branch and model/model_name -> model_id transformation (lines ~190-193)."""
    fake_hf = _inject_langchain_huggingface_module()
    monkeypatch.setitem(sys.modules, 'langchain_huggingface', fake_hf)

    provider = GenericLLMProvider.from_provider('huggingface', chat_log=None, verbose=True, model='hf-model-1', other=7)

    llm = provider.llm
    assert isinstance(llm, fake_hf.ChatHuggingFace)
    # The constructor should receive model_id and not the original 'model' key
    assert llm.kwargs.get('model_id') == 'hf-model-1'
    assert 'model' not in llm.kwargs
    # Other kwargs should be preserved
    assert llm.kwargs.get('other') == 7


def test_bedrock_round_001(monkeypatch):
    """Cover bedrock branch and model/model_name -> model_id plus model_kwargs wrapping (lines ~203-206)."""
    fake_aws = _inject_langchain_aws_module()
    monkeypatch.setitem(sys.modules, 'langchain_aws', fake_aws)

    provider = GenericLLMProvider.from_provider('bedrock', chat_log='x', verbose=False, model_name='bedrock-42', timeout=10)

    llm = provider.llm
    assert isinstance(llm, fake_aws.ChatBedrock)
    # The ChatBedrock should have received model_id and a model_kwargs dict
    assert llm.kwargs.get('model_id') == 'bedrock-42'
    assert isinstance(llm.kwargs.get('model_kwargs'), dict)
    # The original extra kwarg should be inside model_kwargs (model_name was popped)
    assert llm.kwargs['model_kwargs'].get('timeout') == 10


def test_openrouter_round_001(monkeypatch):
    """Cover openrouter branch, rate limiter creation, and environment-driven RPS/API key (lines ~240-257).

    This exercises the InMemoryRateLimiter creation and ensures its attributes propagate into the injected ChatOpenAI call.
    """
    # Inject fake langchain_core.rate_limiters
    pkg, sub = _inject_langchain_core_rate_limiters()
    # Make sure both module names exist in sys.modules so import works
    monkeypatch.setitem(sys.modules, 'langchain_core', pkg)
    monkeypatch.setitem(sys.modules, 'langchain_core.rate_limiters', sub)

    # Inject fake langchain_openai ChatOpenAI as used by openrouter branch
    fake_openai = _inject_langchain_openai_module()
    monkeypatch.setitem(sys.modules, 'langchain_openai', fake_openai)

    # Provide environment variables used in the openrouter branch
    monkeypatch.setenv('OPENROUTER_LIMIT_RPS', '2.5')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'openrouter-secret')

    provider = GenericLLMProvider.from_provider('openrouter', chat_log=None, verbose=True)

    llm = provider.llm
    assert isinstance(llm, fake_openai.ChatOpenAI)
    # The openrouter-created ChatOpenAI should receive the API key from env
    assert llm.kwargs.get('openai_api_key') == 'openrouter-secret'
    # The rate_limiter passed in should be an instance of our fake InMemoryRateLimiter
    rl = llm.kwargs.get('rate_limiter')
    assert rl is not None
    assert hasattr(rl, 'requests_per_second')
    # The provided RPS env var should have been converted to float and applied
    assert abs(rl.requests_per_second - 2.5) < 1e-8
