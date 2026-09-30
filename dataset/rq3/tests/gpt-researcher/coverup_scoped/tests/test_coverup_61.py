# file: gpt_researcher/actions/agent_creator.py:18-62
# asked: {"lines": [41, 42, 44, 45, 46, 47, 48, 49, 51, 52, 53, 54, 55, 58, 59, 61, 62], "branches": []}
# gained: {"lines": [41, 42, 44, 45, 46, 47, 48, 49, 51, 52, 53, 54, 55, 58, 59, 61, 62], "branches": []}

import pytest
from types import SimpleNamespace

@pytest.mark.asyncio
async def test_choose_agent_success_no_parent(monkeypatch):
    # Import module under test (correct path)
    from gpt_researcher.actions import agent_creator

    # Prepare a fake cfg
    cfg = SimpleNamespace(smart_llm_model="test-model", smart_llm_provider="test-provider", llm_kwargs={"k": "v"})

    # Prepare a fake prompt family with auto_agent_instructions method
    class FakePromptFamily:
        @staticmethod
        def auto_agent_instructions():
            return "auto-instructions"

    captured = {}

    async def fake_create_chat_completion(*, model, messages, temperature, llm_provider, llm_kwargs, cost_callback=None, **kwargs):
        # capture inputs for assertions
        captured['model'] = model
        captured['messages'] = messages
        captured['temperature'] = temperature
        captured['llm_provider'] = llm_provider
        captured['llm_kwargs'] = llm_kwargs
        captured['cost_callback'] = cost_callback
        captured['extra_kwargs'] = kwargs
        # return valid JSON string as expected by choose_agent
        return '{"server": "AgentName", "agent_role_prompt": "RolePrompt"}'

    # Monkeypatch the create_chat_completion in the module
    monkeypatch.setattr(agent_creator, "create_chat_completion", fake_create_chat_completion)

    # Call choose_agent without parent_query
    server, role = await agent_creator.choose_agent("do something", cfg, parent_query=None, cost_callback=lambda *a, **k: None, prompt_family=FakePromptFamily)

    # Assertions on return values
    assert server == "AgentName"
    assert role == "RolePrompt"

    # Assertions that the create_chat_completion was called with expected values
    assert captured['model'] == cfg.smart_llm_model
    assert captured['llm_provider'] == cfg.smart_llm_provider
    assert captured['llm_kwargs'] == cfg.llm_kwargs
    # messages should include system with auto instructions and user with task: query
    msgs = captured['messages']
    assert any(m['role'] == 'system' and "auto-instructions" in m['content'] for m in msgs)
    assert any(m['role'] == 'user' and "task: do something" in m['content'] for m in msgs)

@pytest.mark.asyncio
async def test_choose_agent_invalid_json_triggers_handle_json_error(monkeypatch):
    from gpt_researcher.actions import agent_creator

    cfg = SimpleNamespace(smart_llm_model="m", smart_llm_provider="p", llm_kwargs={})

    class FakePromptFamily:
        @staticmethod
        def auto_agent_instructions():
            return "instr"

    captured = {}

    async def fake_create_chat_completion(*, model, messages, temperature, llm_provider, llm_kwargs, cost_callback=None, **kwargs):
        # capture response messages and return invalid JSON
        captured['messages'] = messages
        return "this is not json"

    async def fake_handle_json_error(response):
        # should receive the invalid string returned above
        captured['handle_called_with'] = response
        return ("fallback_server", "fallback_role")

    monkeypatch.setattr(agent_creator, "create_chat_completion", fake_create_chat_completion)
    monkeypatch.setattr(agent_creator, "handle_json_error", fake_handle_json_error)

    server, role = await agent_creator.choose_agent("taskX", cfg, parent_query="parentY", cost_callback=None, prompt_family=FakePromptFamily)

    # The combined query should include parent and child separated by " - "
    msgs = captured['messages']
    assert any(m['role'] == 'user' and "task: parentY - taskX" in m['content'] for m in msgs)

    # The handle_json_error should have been called with the invalid JSON string
    assert captured['handle_called_with'] == "this is not json"
    assert server == "fallback_server"
    assert role == "fallback_role"

@pytest.mark.asyncio
async def test_choose_agent_create_raises_triggers_handle_with_none(monkeypatch):
    from gpt_researcher.actions import agent_creator

    cfg = SimpleNamespace(smart_llm_model="mm", smart_llm_provider="pp", llm_kwargs={})

    class FakePromptFamily:
        @staticmethod
        def auto_agent_instructions():
            return "instr2"

    captured = {}

    async def fake_create_chat_completion(*args, **kwargs):
        # Simulate LLM call raising before returning (response stays None)
        raise RuntimeError("llm failed")

    async def fake_handle_json_error(response):
        # Should receive None because create_chat_completion raised before assigning response
        captured['handle_called_with'] = response
        return ("srv_none", "role_none")

    monkeypatch.setattr(agent_creator, "create_chat_completion", fake_create_chat_completion)
    monkeypatch.setattr(agent_creator, "handle_json_error", fake_handle_json_error)

    server, role = await agent_creator.choose_agent("onlytask", cfg, parent_query=None, cost_callback=None, prompt_family=FakePromptFamily)

    # handle_json_error should be called with None since create_chat_completion never returned
    assert captured['handle_called_with'] is None
    assert server == "srv_none"
    assert role == "role_none"
