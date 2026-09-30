# file: gpt_researcher/mcp/tool_selector.py:129-161
# asked: {"lines": [129, 139, 140, 141, 143, 144, 147, 150, 151, 152, 153, 154, 155, 156, 158, 159, 160, 161], "branches": [[139, 140], [139, 143]]}
# gained: {"lines": [129, 139, 140, 141, 143, 144, 147, 150, 151, 152, 153, 154, 155, 156, 158, 159, 160, 161], "branches": [[139, 140], [139, 143]]}

import sys
import types
import logging
from types import SimpleNamespace

import pytest

from gpt_researcher.mcp.tool_selector import MCPToolSelector


@pytest.mark.asyncio
async def test_call_llm_no_cfg_returns_empty_and_logs_warning(caplog):
    # Arrange: selector with no cfg
    selector = MCPToolSelector(cfg=None, researcher=None)

    # Act
    caplog.set_level(logging.WARNING)
    result = await selector._call_llm_for_tool_selection("prompt text")

    # Assert
    assert result == ""
    assert "No config available for LLM call" in caplog.text


@pytest.mark.asyncio
async def test_call_llm_success_calls_create_chat_completion_with_expected_args(monkeypatch):
    # Arrange: prepare cfg and researcher
    cfg = SimpleNamespace(
        strategic_llm_model="strategic-model-v1",
        strategic_llm_provider="provider-x",
        llm_kwargs={"foo": "bar"},
    )

    class Researcher:
        def __init__(self):
            self.costs_added = []

        def add_costs(self, *args, **kwargs):
            # sentinel to verify it's passed through
            self.costs_added.append((args, kwargs))

    researcher = Researcher()
    selector = MCPToolSelector(cfg=cfg, researcher=researcher)

    # Prepare a fake llm module with an async create_chat_completion that captures inputs
    captured = {}

    async def fake_create_chat_completion(model, messages, temperature, llm_provider, llm_kwargs, cost_callback=None):
        # capture the incoming parameters for assertions
        captured['model'] = model
        captured['messages'] = messages
        captured['temperature'] = temperature
        captured['llm_provider'] = llm_provider
        captured['llm_kwargs'] = llm_kwargs
        captured['cost_callback'] = cost_callback
        # Do not assert identity of bound method (bound method objects are not 'is' identical on each access)
        return "LLM selection result"

    mod_name = "gpt_researcher.utils.llm"
    llm_mod = types.ModuleType(mod_name)
    llm_mod.create_chat_completion = fake_create_chat_completion
    # Inject into sys.modules so the in-function import finds it
    monkeypatch.setitem(sys.modules, mod_name, llm_mod)

    # Act
    prompt = "Please select tools for me."
    result = await selector._call_llm_for_tool_selection(prompt)

    # Assert returned result and that create_chat_completion received expected parameters
    assert result == "LLM selection result"
    assert captured['model'] == cfg.strategic_llm_model
    assert captured['temperature'] == 0.0
    assert captured['llm_provider'] == cfg.strategic_llm_provider
    assert captured['llm_kwargs'] == cfg.llm_kwargs
    # messages should be a single user role with the prompt content
    assert isinstance(captured['messages'], list)
    assert captured['messages'][0]['role'] == 'user'
    assert captured['messages'][0]['content'] == prompt
    # cost_callback should be provided and callable; invoke to verify it calls researcher's method
    cost_cb = captured.get('cost_callback')
    assert cost_cb is not None and callable(cost_cb)
    # Calling cost_cb should record costs in the researcher
    cost_cb("test", value=1)
    assert researcher.costs_added, "researcher.add_costs should have been callable and recorded a call"
    # verify the recorded args match what we invoked
    recorded_args, recorded_kwargs = researcher.costs_added[-1]
    assert recorded_args == ("test",)
    assert recorded_kwargs == {"value": 1}


@pytest.mark.asyncio
async def test_call_llm_exception_is_handled_and_logs_error(monkeypatch, caplog):
    # Arrange: cfg present but create_chat_completion will raise
    cfg = SimpleNamespace(
        strategic_llm_model="m",
        strategic_llm_provider="p",
        llm_kwargs={},
    )
    selector = MCPToolSelector(cfg=cfg, researcher=None)

    async def raising_create_chat_completion(*args, **kwargs):
        raise RuntimeError("boom")

    mod_name = "gpt_researcher.utils.llm"
    llm_mod = types.ModuleType(mod_name)
    llm_mod.create_chat_completion = raising_create_chat_completion
    monkeypatch.setitem(sys.modules, mod_name, llm_mod)

    # Act
    caplog.set_level(logging.ERROR)
    result = await selector._call_llm_for_tool_selection("prompt for error")

    # Assert
    assert result == ""
    assert "Error calling LLM for tool selection: boom" in caplog.text
