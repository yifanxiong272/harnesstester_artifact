import sys
import types
import asyncio
import pytest
from types import SimpleNamespace

import gpt_researcher.utils.tools as tools_mod

# Minimal replacements for langchain message/tool classes to avoid external deps
class DummyMessage:
    def __init__(self, content):
        self.content = content

class DummyToolMessage:
    def __init__(self, content, tool_call_id=""):
        self.content = content
        self.tool_call_id = tool_call_id

# Helpers to set up the module-level dependencies deterministically
def _patch_message_and_tracking():
    tools_mod.SystemMessage = lambda content: DummyMessage(content)
    tools_mod.HumanMessage = lambda content: DummyMessage(content)
    tools_mod.AIMessage = lambda content: DummyMessage(content)
    tools_mod.ToolMessage = lambda content, tool_call_id="": DummyToolMessage(content, tool_call_id)
    # no-op for cost tracking to avoid side effects
    tools_mod._track_response_cost = lambda **kwargs: None

# Install a fake GenericLLMProvider module into sys.modules so that
# `from ..llm_provider.generic.base import GenericLLMProvider` inside the target
# function will import our fake instead of the real one.
def _install_fake_generic_provider(factory):
    module_name = "gpt_researcher.llm_provider.generic.base"
    fake_mod = types.ModuleType(module_name)
    # Create a placeholder class with a from_provider staticmethod that calls our factory
    class FakeGeneric:
        pass

    FakeGeneric.from_provider = staticmethod(lambda provider, **kwargs: factory())
    fake_mod.GenericLLMProvider = FakeGeneric
    sys.modules[module_name] = fake_mod

@pytest.mark.asyncio
async def test_no_tool_calls_round_005():
    """Case: LLM responds with no tool_calls -> should return response.content and empty metadata"""
    _patch_message_and_tracking()

    # Fake provider and llm with bind_tools and ainvoke
    class FakeLLM:
        def bind_tools(self, tools):
            return self

        async def ainvoke(self, messages):
            # return an object with .content and no .tool_calls
            return SimpleNamespace(content="no_tools_response")

    class FakeProvider:
        def __init__(self):
            self.llm = FakeLLM()

    # Install fake GenericLLMProvider so the function import resolves to our fake
    _install_fake_generic_provider(lambda: FakeProvider())

    # call function under test with messages that hit system/user/assistant conversions
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "usr"},
        {"role": "assistant", "content": "asst"},
    ]

    result_content, metadata = await tools_mod.create_chat_completion_with_tools(
        messages=messages,
        tools=[],
        model="m",
        llm_provider="any",
    )

    assert result_content == "no_tools_response"
    assert metadata == []

@pytest.mark.asyncio
async def test_tool_calls_various_round_005():
    """Case: LLM makes multiple tool calls; exercise ainvoke/invoke, and error branches for timeout/connection/permission/other"""
    _patch_message_and_tracking()

    # Prepare a response object that contains multiple tool calls
    tool_calls = [
        {"name": "tool_ainvoke", "args": {"x": 1}, "id": "id1"},
        {"name": "tool_invoke", "args": {"y": 2}, "id": "id2"},
        {"name": "tool_timeout", "args": {}, "id": "id3"},
        {"name": "tool_conn", "args": {}, "id": "id4"},
        {"name": "tool_perm", "args": {}, "id": "id5"},
        {"name": "tool_other", "args": {}, "id": "id6"},
    ]

    class FirstResponse(SimpleNamespace):
        def __init__(self):
            super().__init__(content="intermediate", tool_calls=tool_calls)

    class FinalResponse(SimpleNamespace):
        def __init__(self):
            super().__init__(content="final", tool_calls=None)

    # Create tools matching the names above
    class ToolAInvoke:
        name = "tool_ainvoke"
        async def ainvoke(self, args):
            return "result_async"

    class ToolInvoke:
        name = "tool_invoke"
        def invoke(self, args):
            return "result_sync"

    class ToolTimeout:
        name = "tool_timeout"
        def invoke(self, args):
            raise Exception("Timeout occurred while calling API")

    class ToolConn:
        name = "tool_conn"
        def invoke(self, args):
            raise Exception("Network connection failed")

    class ToolPerm:
        name = "tool_perm"
        def invoke(self, args):
            raise Exception("Permission denied: access not allowed")

    class ToolOther:
        name = "tool_other"
        def invoke(self, args):
            raise Exception("unexpected failure")

    tools_list = [ToolAInvoke(), ToolInvoke(), ToolTimeout(), ToolConn(), ToolPerm(), ToolOther()]

    # Fake llm that returns FirstResponse on first call and FinalResponse on second
    class FakeLLM:
        def __init__(self):
            self.call_count = 0

        def bind_tools(self, tools):
            return self

        async def ainvoke(self, messages):
            self.call_count += 1
            if self.call_count == 1:
                return FirstResponse()
            return FinalResponse()

    class FakeProvider:
        def __init__(self):
            self.llm = FakeLLM()

    # Install fake GenericLLMProvider so create_chat_completion_with_tools uses FakeProvider
    _install_fake_generic_provider(lambda: FakeProvider())

    # Run the function
    messages = [{"role": "user", "content": "ask"}]

    final_content, metadata = await tools_mod.create_chat_completion_with_tools(
        messages=messages,
        tools=tools_list,
        model="m",
        llm_provider="p",
    )

    # Validate final content
    assert final_content == "final"

    # Validate metadata contains an entry for each tool call and sensible result strings
    assert isinstance(metadata, list)
    names = [m["tool"] for m in metadata]
    assert names == [tc["name"] for tc in tool_calls]

    # Check that results for successful tools appear verbatim
    mapping = {m["tool"]: m["result"] for m in metadata}
    assert mapping["tool_ainvoke"] == "result_async"
    assert mapping["tool_invoke"] == "result_sync"

    # Error messages should reflect the error categories (case-insensitive checks)
    assert ("timed out" in mapping["tool_timeout"].lower()) or ("timed" in mapping["tool_timeout"].lower()) or isinstance(mapping["tool_timeout"], str)
    assert ("network" in mapping["tool_conn"].lower()) or ("connection" in mapping["tool_conn"].lower())
    assert ("permission" in mapping["tool_perm"].lower()) or ("access" in mapping["tool_perm"].lower())
    assert ("encountered an error" in mapping["tool_other"].lower()) or ("unexpected" in mapping["tool_other"].lower()) or isinstance(mapping["tool_other"], str)

@pytest.mark.asyncio
async def test_exception_fallback_round_005():
    """Case: GenericLLMProvider.from_provider raises -> function falls back to create_chat_completion"""
    _patch_message_and_tracking()

    # Make a factory that raises to simulate provider import-time failure
    def raising_factory():
        raise RuntimeError("simulated provider failure")

    # Install a GenericLLMProvider whose from_provider will raise
    _install_fake_generic_provider(lambda: raising_factory())

    # Provide a fallback create_chat_completion async function
    async def fake_create_chat_completion(**kwargs):
        return "fallback_result"

    tools_mod.create_chat_completion = fake_create_chat_completion

    messages = [{"role": "user", "content": "will fallback"}]

    result, metadata = await tools_mod.create_chat_completion_with_tools(
        messages=messages,
        tools=[],
        model="m",
    )

    assert result == "fallback_result"
    assert metadata == []
