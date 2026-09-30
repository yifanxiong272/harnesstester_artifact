import pytest

from gpt_researcher.actions import agent_creator


class DummyCfg:
    smart_llm_model = "model-x"
    smart_llm_provider = "provider-x"
    llm_kwargs = {"k": "v"}


class DummyPromptFamily:
    def __init__(self, instr):
        self._instr = instr

    def auto_agent_instructions(self):
        return self._instr


@pytest.mark.asyncio
async def test_choose_agent_success_with_parent_round_156(monkeypatch):
    """Success path: create_chat_completion returns well-formed JSON.

    Verifies:
    - The returned tuple matches parsed JSON.
    - The user message contains both parent and child query (covers the parent_query formatting branch).
    """

    captured = {}

    async def fake_create_chat_completion(*, model, messages, temperature, llm_provider, llm_kwargs, cost_callback, **kwargs):
        # capture the messages passed in for assertions
        captured["messages"] = messages
        # return deterministic, valid JSON string
        return '{"server": "AgentX", "agent_role_prompt": "RolePrompt"}'

    # Patch the create_chat_completion used by the module under test
    monkeypatch.setattr(agent_creator, "create_chat_completion", fake_create_chat_completion)

    cfg = DummyCfg()
    prompt = DummyPromptFamily("AUTO_INSTR")

    server, role = await agent_creator.choose_agent(
        "child_query",
        cfg,
        parent_query="parent_query",
        prompt_family=prompt,
    )

    assert server == "AgentX"
    assert role == "RolePrompt"

    # Ensure the user message contains the parent and child queries (verifies line 41 formatting)
    user_msg = next((m for m in captured["messages"] if m.get("role") == "user"), None)
    assert user_msg is not None
    assert "parent_query" in user_msg["content"]
    assert "child_query" in user_msg["content"]


@pytest.mark.asyncio
async def test_choose_agent_invalid_json_calls_handle_error_round_156(monkeypatch):
    """Error path: create_chat_completion returns invalid JSON string causing json.loads to raise.

    Verifies:
    - The module falls into the except branch and calls handle_json_error with the raw response.
    - The returned value from the patched handle_json_error is propagated.
    """

    async def fake_create_chat_completion(*args, **kwargs):
        return "NOT A JSON"

    called = {}

    async def fake_handle_json_error(response):
        # record what was passed in so we can assert it
        called["response"] = response
        return ("fallback_server", "fallback_prompt")

    monkeypatch.setattr(agent_creator, "create_chat_completion", fake_create_chat_completion)
    monkeypatch.setattr(agent_creator, "handle_json_error", fake_handle_json_error)

    cfg = DummyCfg()
    prompt = DummyPromptFamily("AUTO_INSTR")

    server, role = await agent_creator.choose_agent("q", cfg, prompt_family=prompt)

    assert server == "fallback_server"
    assert role == "fallback_prompt"
    # Ensure handle_json_error was called with the exact invalid response
    assert called.get("response") == "NOT A JSON"
