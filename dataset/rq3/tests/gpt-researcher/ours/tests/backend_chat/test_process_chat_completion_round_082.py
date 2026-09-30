import asyncio
import pytest

from backend.chat import chat

# All tests in this file are deterministic and patch external calls.

class DummyConfig:
    def __init__(self, *args, **kwargs):
        # Only attributes used by process_chat_completion
        self.smart_llm_model = "dummy-model"
        self.smart_llm_provider = "dummy-provider"
        self.llm_kwargs = {}


@pytest.mark.asyncio
async def test_process_chat_completion_with_query_round_082(monkeypatch):
    """When tool metadata contains a non-empty query, quick_search should be invoked and
    processed_metadata should include the agent.search_metadata populated by quick_search.
    """
    # Patch Config used in ChatAgentWithMemory.__init__ so constructing is safe
    monkeypatch.setattr(chat, "Config", DummyConfig)

    # Prepare recording containers
    create_search_tool_calls = []
    create_chat_calls = {}

    # Stub for create_search_tool: record the callable passed and return a sentinel tool object
    def fake_create_search_tool(callable_quick_search):
        create_search_tool_calls.append(callable_quick_search)
        return {"name": "search_tool_obj"}

    # Stub for create_chat_completion_with_tools: async and deterministic
    async def fake_create_chat_completion_with_tools(messages, tools, model, llm_provider, llm_kwargs):
        # record inputs for later assertions
        create_chat_calls["messages"] = messages
        create_chat_calls["tools"] = tools
        create_chat_calls["model"] = model
        # Return a response and tool_calls_metadata indicating a search with a non-empty query
        tool_calls_metadata = [
            {"tool": "search_tool", "args": {"query": "python"}}
        ]
        return ("dummy-response", tool_calls_metadata)

    monkeypatch.setattr(chat, "create_search_tool", fake_create_search_tool)
    monkeypatch.setattr(chat, "create_chat_completion_with_tools", fake_create_chat_completion_with_tools)

    # Instantiate agent
    agent = chat.ChatAgentWithMemory(report="report-text", config_path="unused")

    # Replace agent.quick_search with a deterministic stub that sets search_metadata
    def fake_quick_search(q):
        agent.search_metadata = {"query": q, "sources": [{"title": "t", "url": "u"}], "note": "populated"}
        return {"results": []}

    agent.quick_search = fake_quick_search

    # Call the async method under test
    response, processed_metadata = await agent.process_chat_completion(messages=[{"role": "user", "content": "hi"}])

    # Assertions: response forwarded, create_search_tool was used to create a tool, and quick_search was invoked
    assert response == "dummy-response"
    # create_search_tool should have been called with the agent.quick_search callable
    assert create_search_tool_calls, "create_search_tool was not called"
    assert create_search_tool_calls[0] is fake_quick_search

    # create_chat_completion_with_tools should receive the tool produced by fake_create_search_tool
    assert create_chat_calls.get("tools") == [{"name": "search_tool_obj"}]

    # processed_metadata should reflect the quick_search results stored on the agent
    assert isinstance(processed_metadata, list) and len(processed_metadata) == 1
    item = processed_metadata[0]
    assert item["tool"] == "quick_search"
    assert item["query"] == "python"
    assert item["search_metadata"] == agent.search_metadata


@pytest.mark.asyncio
async def test_process_chat_completion_empty_query_and_nonsearch_tool_round_082(monkeypatch):
    """Covers branches where:
    - metadata contains a search_tool with an empty query (should not call quick_search)
    - metadata entries whose tool is not 'search_tool' are ignored
    """
    monkeypatch.setattr(chat, "Config", DummyConfig)

    # Stubs and recorders
    created_tools = []

    def fake_create_search_tool(callable_quick_search):
        created_tools.append(callable_quick_search)
        return {"name": "search_tool_obj"}

    async def fake_create_chat_completion_with_tools(messages, tools, model, llm_provider, llm_kwargs):
        # Return two metadata entries: one non-search tool and one search_tool with empty query
        tool_calls_metadata = [
            {"tool": "other_tool", "args": {"x": 1}},
            {"tool": "search_tool", "args": {"query": ""}}
        ]
        return ("resp-empty-query", tool_calls_metadata)

    monkeypatch.setattr(chat, "create_search_tool", fake_create_search_tool)
    monkeypatch.setattr(chat, "create_chat_completion_with_tools", fake_create_chat_completion_with_tools)

    agent = chat.ChatAgentWithMemory(report="r2", config_path="unused")

    # Replace quick_search with a function that would mutate search_metadata if called
    def fake_quick_search_mutating(q):
        # If called (which it shouldn't for empty query), mutate search_metadata to a sentinel
        agent.search_metadata = {"called_with": q}

    agent.quick_search = fake_quick_search_mutating

    # Ensure initial search_metadata is None
    assert agent.search_metadata is None

    response, processed_metadata = await agent.process_chat_completion(messages=[{"role": "user", "content": "hi"}])

    # Response should match stub and processed_metadata should have two entries processed only for search_tool
    assert response == "resp-empty-query"

    # Only the search_tool entry should be added to processed_metadata; its query is empty and search_metadata remains None
    assert isinstance(processed_metadata, list) and len(processed_metadata) == 1
    md = processed_metadata[0]
    assert md["tool"] == "quick_search"
    assert md["query"] == ""
    # quick_search should NOT have been invoked (search_metadata remains as it was)
    assert agent.search_metadata is None

    # Also ensure create_search_tool was called and passed our agent.quick_search callable
    assert created_tools and created_tools[0] is fake_quick_search_mutating
