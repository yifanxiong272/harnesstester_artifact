# file: multi_agents_ag2/agents/editor.py:17-41
# asked: {"lines": [17, 18, 19, 20, 21, 22, 24, 25, 28, 29, 31, 32, 33, 34, 37, 38, 39, 40], "branches": []}
# gained: {"lines": [17], "branches": []}

import pytest

@pytest.mark.asyncio
async def test_plan_research_executes_lines_in_ag2_module(monkeypatch):
    # Skip test if the target module is not present
    editor_mod = pytest.importorskip("multi_agents_ag2.agents.editor")
    EditorAgent = getattr(editor_mod, "EditorAgent")

    agent = EditorAgent()

    # Prepare research_state with human feedback included
    research_state = {
        "initial_research": {"key": "value"},
        "human_feedback": {"comment": "expand"},
        "task": {
            "include_human_feedback": True,
            "max_sections": 3,
            "model": "ag2-model",
        },
    }

    created_prompts = []
    printed = []
    called_models = []

    # Stub the instance method _create_planning_prompt
    def fake_create_prompt(initial_research, include_human_feedback, human_feedback, max_sections):
        created_prompts.append((initial_research, include_human_feedback, human_feedback, max_sections))
        return "AG2_PROMPT"

    monkeypatch.setattr(agent, "_create_planning_prompt", fake_create_prompt)

    # Stub module-level print_agent_output
    def fake_print_agent_output(message, agent=""):
        printed.append((message, agent))

    monkeypatch.setattr(editor_mod, "print_agent_output", fake_print_agent_output)

    # Stub async call_model
    async def fake_call_model(prompt=None, model=None, response_format=None):
        called_models.append((prompt, model, response_format))
        return {"title": "AG2 Title", "date": "2077-07-07", "sections": ["s1", "s2"]}

    monkeypatch.setattr(editor_mod, "call_model", fake_call_model)

    # Call the coroutine under test
    result = await agent.plan_research(research_state)

    # Assertions to ensure lines executed and behavior as expected
    assert len(created_prompts) == 1
    ir, inc_hf, hf, max_secs = created_prompts[0]
    assert ir == research_state["initial_research"]
    assert inc_hf is True
    assert hf == research_state["human_feedback"]
    assert max_secs == 3

    assert printed == [("Planning an outline layout based on initial research...", "EDITOR")]

    assert len(called_models) == 1
    prompt_arg, model_arg, rf_arg = called_models[0]
    assert prompt_arg == "AG2_PROMPT"
    assert model_arg == research_state["task"]["model"]
    assert rf_arg == "json"

    assert result == {"title": "AG2 Title", "date": "2077-07-07", "sections": ["s1", "s2"]}


@pytest.mark.asyncio
async def test_plan_research_executes_lines_in_multi_agents_module_if_present(monkeypatch):
    # Some environments may expose the editor at multi_agents.agents.editor.
    # If not present, skip this test.
    editor_mod = pytest.importorskip("multi_agents.agents.editor")
    EditorAgent = getattr(editor_mod, "EditorAgent")

    agent = EditorAgent()

    # Prepare research_state without human_feedback key to exercise None handling
    research_state = {
        "initial_research": {"x": 2},
        "task": {
            "include_human_feedback": False,
            "max_sections": 1,
            "model": "ma-model",
        },
    }

    created_prompts = []
    printed = []
    called_models = []

    def fake_create_prompt(initial_research, include_human_feedback, human_feedback, max_sections):
        created_prompts.append((initial_research, include_human_feedback, human_feedback, max_sections))
        return f"MA_PROMPT_{max_sections}"

    monkeypatch.setattr(agent, "_create_planning_prompt", fake_create_prompt)

    def fake_print_agent_output(message, agent=""):
        printed.append((message, agent))

    monkeypatch.setattr(editor_mod, "print_agent_output", fake_print_agent_output)

    async def fake_call_model(prompt=None, model=None, response_format=None):
        called_models.append((prompt, model, response_format))
        # Intentionally return missing fields to ensure .get() usage is exercised
        return {"title": "MA Title", "date": None, "sections": ["only"]}

    monkeypatch.setattr(editor_mod, "call_model", fake_call_model)

    result = await agent.plan_research(research_state)

    # Validate prompt creation captured human_feedback as None
    assert len(created_prompts) == 1
    ir, inc_hf, hf, max_secs = created_prompts[0]
    assert ir == research_state["initial_research"]
    assert inc_hf is False
    assert hf is None
    assert max_secs == 1

    assert printed == [("Planning an outline layout based on initial research...", "EDITOR")]

    assert len(called_models) == 1
    prompt_arg, model_arg, rf_arg = called_models[0]
    assert prompt_arg == "MA_PROMPT_1"
    assert model_arg == research_state["task"]["model"]
    assert rf_arg == "json"

    assert result == {"title": "MA Title", "date": None, "sections": ["only"]}
