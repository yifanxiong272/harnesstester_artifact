import asyncio
import json
import os
import pytest

from browser_use.mcp import server

# Fake classes and helpers used to deterministically simulate LLMs and Agent behavior
class FakeBedrock:
    last_init = None

    def __init__(self, model, aws_region, aws_sso_auth):
        # record constructor args for assertions
        FakeBedrock.last_init = {"model": model, "aws_region": aws_region, "aws_sso_auth": aws_sso_auth}


class FakeChatOpenAI:
    last_init = None

    def __init__(self, model, api_key, temperature, **kwargs):
        FakeChatOpenAI.last_init = {"model": model, "api_key": api_key, "temperature": temperature, **kwargs}


class FakeBrowserProfile:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeHistory:
    def __init__(self, steps, success=True, final=None, errors=None, urls=None):
        self.history = list(range(steps))
        self._success = success
        self._final = final
        self._errors = errors or []
        self._urls = urls or []

    def is_successful(self):
        return self._success

    def final_result(self):
        return self._final

    def errors(self):
        return self._errors

    def urls(self):
        return self._urls


class AgentFake:
    # configurable by tests via class attributes
    next_history = None
    raise_on_run = None
    closed = False
    last_init_kwargs = None

    def __init__(self, *args, **kwargs):
        AgentFake.last_init_kwargs = {"args": args, "kwargs": kwargs}

    async def run(self, max_steps=100):
        if AgentFake.raise_on_run:
            raise AgentFake.raise_on_run
        return AgentFake.next_history

    async def close(self):
        AgentFake.closed = True


@pytest.mark.asyncio
async def test_bedrock_branch_default_region_and_final_result_urls_round_073(monkeypatch):
    """
    Exercise the Bedrock branch where region is not provided and should default to 'us-east-1'.
    Also return a history with a final_result and non-empty URLs to assert formatting.
    """
    # Patch llm/profile/agent constructors resolved in the server module
    monkeypatch.setattr(server, "ChatAWSBedrock", FakeBedrock)
    monkeypatch.setattr(server, "ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr(server, "BrowserProfile", FakeBrowserProfile)
    monkeypatch.setattr(server, "Agent", AgentFake)

    # Provide llm config indicating bedrock provider but NO region key to force default
    monkeypatch.setattr(server, "get_default_llm", lambda cfg: {"model_provider": "bedrock", "aws_sso_auth": False})
    # Provide a default profile for BrowserProfile
    monkeypatch.setattr(server, "get_default_profile", lambda cfg: {"some": "value"})

    # Prepare agent behavior: successful, final_result present, urls contain a URL and None to exercise filtering
    AgentFake.next_history = FakeHistory(steps=3, success=True, final="done", errors=[], urls=["https://example.test", None])
    AgentFake.raise_on_run = None
    AgentFake.closed = False

    # Create a server instance placeholder with minimal config attribute used by get_default_* calls
    class DummyServer:
        def __init__(self):
            self.config = {}

    s = DummyServer()

    result = await server.BrowserUseServer._retry_with_browser_use_agent(s, task="do something", max_steps=5, model=None, allowed_domains=None, use_vision=True)

    # Assertions: content and that the Bedrock constructor received default region
    assert "Task completed in 3 steps" in result
    assert "Success: True" in result
    # Final result should be included
    assert "Final result" in result and "done" in result
    # URLs visited should be included and the example URL present
    assert "URLs visited:" in result and "https://example.test" in result
    # Check FakeBedrock captured the default aws_region as 'us-east-1'
    assert FakeBedrock.last_init is not None
    assert FakeBedrock.last_init["aws_region"] == "us-east-1"
    # Agent close should have been awaited in finally
    assert AgentFake.closed is True


@pytest.mark.asyncio
async def test_openai_missing_api_key_returns_error_round_073(monkeypatch):
    """
    When model_provider is not bedrock and no api_key is present in config or environment,
    the function must return the explicit error string.
    """
    # Ensure no env var and get_default_llm returns no api_key
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(server, "get_default_llm", lambda cfg: {})

    class DummyServer:
        def __init__(self):
            self.config = {}

    s = DummyServer()

    res = await server.BrowserUseServer._retry_with_browser_use_agent(s, task="noop", max_steps=1, model=None, allowed_domains=None, use_vision=False)
    assert res == "Error: OPENAI_API_KEY not set in config or environment"


@pytest.mark.asyncio
async def test_openai_with_base_url_and_errors_and_none_urls_round_073(monkeypatch):
    """
    Exercise the OpenAI path when base_url is provided and history has errors but no final_result and urls are None-only.
    This covers base_url kwargs handling, errors formatting, and the branch where no URLs are appended.
    """
    # Provide api_key and base_url in default llm config
    def llm_cfg(cfg):
        return {"model_provider": "openai", "api_key": "test-key", "base_url": "https://custom.api", "temperature": 0.0}

    monkeypatch.setattr(server, "get_default_llm", llm_cfg)
    monkeypatch.setattr(server, "ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr(server, "BrowserProfile", FakeBrowserProfile)
    monkeypatch.setattr(server, "Agent", AgentFake)
    monkeypatch.setattr(server, "get_default_profile", lambda cfg: {"allowed_domains": ["allowed.test"]})

    # History: no final_result, has errors, urls contains only None so valid_urls becomes empty
    AgentFake.next_history = FakeHistory(steps=2, success=False, final=None, errors=[{"msg": "err1"}], urls=[None])
    AgentFake.raise_on_run = None
    AgentFake.closed = False

    class DummyServer:
        def __init__(self):
            self.config = {}

    s = DummyServer()

    res = await server.BrowserUseServer._retry_with_browser_use_agent(s, task="check errors", max_steps=2, model=None, allowed_domains=["allowed.test"], use_vision=False)

    # Ensure ChatOpenAI received base_url in its recorded initialization
    assert FakeChatOpenAI.last_init is not None
    assert FakeChatOpenAI.last_init.get("base_url") == "https://custom.api"

    # The results should include the step count and success flag
    assert "Task completed in 2 steps" in res
    assert "Success: False" in res
    # Errors should be included as JSON
    assert "Errors encountered" in res
    assert "err1" in res
    # Since urls list had only None, no 'URLs visited' section should be present
    assert "URLs visited:" not in res
    # Agent close should have been awaited
    assert AgentFake.closed is True


@pytest.mark.asyncio
async def test_agent_run_raises_closes_agent_round_073(monkeypatch):
    """
    Simulate Agent.run raising an exception to exercise the except branch and ensure agent.close is still awaited.
    """
    monkeypatch.setattr(server, "get_default_llm", lambda cfg: {"model_provider": "openai", "api_key": "k"})
    monkeypatch.setattr(server, "ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr(server, "BrowserProfile", FakeBrowserProfile)
    monkeypatch.setattr(server, "Agent", AgentFake)
    monkeypatch.setattr(server, "get_default_profile", lambda cfg: {})

    AgentFake.next_history = None
    AgentFake.raise_on_run = RuntimeError("boom")
    AgentFake.closed = False

    class DummyServer:
        def __init__(self):
            self.config = {}

    s = DummyServer()

    res = await server.BrowserUseServer._retry_with_browser_use_agent(s, task="explode", max_steps=1, model=None, allowed_domains=None, use_vision=False)
    assert res.startswith("Agent task failed:")
    assert "boom" in res
    # Agent close should have been awaited even on exception
    assert AgentFake.closed is True
