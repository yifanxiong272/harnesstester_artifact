import sys
import types
import pytest
from gpt_researcher.mcp.tool_selector import MCPToolSelector

@pytest.mark.asyncio
async def test_no_cfg_round_103():
    """When cfg is falsy the method should warn and return an empty string."""
    selector = MCPToolSelector(cfg=None, researcher=None)
    result = await selector._call_llm_for_tool_selection("irrelevant prompt")
    assert result == ""

@pytest.mark.asyncio
async def test_successful_llm_call_round_103(monkeypatch):
    """Simulate a successful async create_chat_completion and verify inputs and cost callback usage.

    We inject a fake gpt_researcher.utils.llm module into sys.modules so the local import
    inside _call_llm_for_tool_selection resolves to our stub.
    """
    captured = {}

    fake_mod = types.ModuleType("gpt_researcher.utils.llm")

    async def create_chat_completion(model, messages, temperature, llm_provider, llm_kwargs, cost_callback):
        # Capture the parameters so we can assert them after the call
        captured['model'] = model
        captured['messages'] = messages
        captured['temperature'] = temperature
        captured['llm_provider'] = llm_provider
        captured['llm_kwargs'] = llm_kwargs
        captured['cost_callback'] = cost_callback
        # If a cost callback was provided, call it to ensure the selector passes through the bound method
        if cost_callback:
            cost_callback(0.42)
        return "LLM_OK"

    fake_mod.create_chat_completion = create_chat_completion
    monkeypatch.setitem(sys.modules, "gpt_researcher.utils.llm", fake_mod)

    class FakeCfg:
        strategic_llm_model = "strategic-model"
        strategic_llm_provider = "fake-provider"
        llm_kwargs = {"kw": "val"}

    costs = []

    class FakeResearcher:
        def add_costs(self, c):
            costs.append(c)

    selector = MCPToolSelector(cfg=FakeCfg(), researcher=FakeResearcher())
    out = await selector._call_llm_for_tool_selection("choose tool A")

    assert out == "LLM_OK"
    # messages should wrap the prompt in the expected structure
    assert captured['messages'] == [{"role": "user", "content": "choose tool A"}]
    # ensure a deterministic temperature was passed
    assert captured['temperature'] == 0.0
    # provider and model forwarded
    assert captured['model'] == "strategic-model"
    assert captured['llm_provider'] == "fake-provider"
    assert captured['llm_kwargs'] == {"kw": "val"}
    # cost callback should have been called and modified our costs list
    assert costs == [0.42]

@pytest.mark.asyncio
async def test_llm_exception_round_103(monkeypatch):
    """If create_chat_completion raises, the selector should catch and return an empty string."""
    fake_mod = types.ModuleType("gpt_researcher.utils.llm")

    async def create_chat_completion(*args, **kwargs):
        raise RuntimeError("simulated failure")

    fake_mod.create_chat_completion = create_chat_completion
    monkeypatch.setitem(sys.modules, "gpt_researcher.utils.llm", fake_mod)

    class FakeCfg2:
        strategic_llm_model = "m"
        strategic_llm_provider = "p"
        llm_kwargs = {}

    selector = MCPToolSelector(cfg=FakeCfg2(), researcher=None)
    result = await selector._call_llm_for_tool_selection("will fail")
    assert result == ""
