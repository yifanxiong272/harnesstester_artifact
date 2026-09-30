import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest

# Load the editor module directly from file to avoid executing package __init__
# (which imports other modules requiring unavailable dependencies like 'autogen').

def _make_editor_module():
    path = Path("multi_agents_ag2/agents/editor.py").resolve()
    spec = importlib.util.spec_from_file_location("_test_multi_agents_ag2_agents_editor", path)
    module = importlib.util.module_from_spec(spec)
    # Execute the module in its own namespace without importing package __init__
    loader = spec.loader
    assert loader is not None
    loader.exec_module(module)
    return module


def test_plan_research_includes_human_feedback_round_149(monkeypatch):
    module = _make_editor_module()
    EditorAgent = module.EditorAgent

    # Create an instance without calling __init__
    agent = object.__new__(EditorAgent)

    research_state = {
        "initial_research": {"summary": "initial"},
        "human_feedback": {"note": "please expand"},
        "task": {
            "include_human_feedback": True,
            "max_sections": 5,
            "model": "gpt-test-model",
        },
    }

    prompt_called = {}

    def fake_create_prompt(initial_research, include_human_feedback, human_feedback, max_sections):
        prompt_called["args"] = (initial_research, include_human_feedback, human_feedback, max_sections)
        return "DUMMY_PROMPT"

    agent._create_planning_prompt = fake_create_prompt

    printed = {}

    def fake_print_agent_output(message, agent: str = None):
        printed["message"] = message
        printed["agent"] = agent

    monkeypatch.setattr(module, "print_agent_output", fake_print_agent_output)

    async def fake_call_model(prompt, model, response_format="json"):
        assert prompt == "DUMMY_PROMPT"
        assert model == research_state["task"]["model"]
        assert response_format == "json"
        return {"title": "Test Title", "date": "2026-09-01", "sections": [{"heading": "Intro"}]}

    monkeypatch.setattr(module, "call_model", fake_call_model)

    result = asyncio.run(agent.plan_research(research_state))

    assert "args" in prompt_called
    ir, ihf, hf, ms = prompt_called["args"]
    assert ir == research_state["initial_research"]
    assert ihf is True
    assert hf == research_state["human_feedback"]
    assert ms == research_state["task"]["max_sections"]

    assert "message" in printed and isinstance(printed["message"], str)
    assert printed["agent"] == "EDITOR"

    assert result["title"] == "Test Title"
    assert result["date"] == "2026-09-01"
    assert isinstance(result["sections"], list)
    assert result["sections"][0]["heading"] == "Intro"


def test_plan_research_excludes_human_feedback_round_149(monkeypatch):
    module = _make_editor_module()
    EditorAgent = module.EditorAgent

    agent = object.__new__(EditorAgent)

    research_state = {
        "initial_research": {"summary": "initial without feedback"},
        "task": {
            "include_human_feedback": False,
            "max_sections": 2,
            "model": "gpt-test-model-2",
        },
    }

    prompt_called = {}

    def fake_create_prompt(initial_research, include_human_feedback, human_feedback, max_sections):
        prompt_called["args"] = (initial_research, include_human_feedback, human_feedback, max_sections)
        return "DUMMY_PROMPT_NO_HF"

    agent._create_planning_prompt = fake_create_prompt

    printed = {}

    def fake_print_agent_output(message, agent: str = None):
        printed["message"] = message
        printed["agent"] = agent

    monkeypatch.setattr(module, "print_agent_output", fake_print_agent_output)

    async def fake_call_model(prompt, model, response_format="json"):
        assert prompt == "DUMMY_PROMPT_NO_HF"
        assert model == research_state["task"]["model"]
        assert response_format == "json"
        return {"title": None, "date": None, "sections": []}

    monkeypatch.setattr(module, "call_model", fake_call_model)

    result = asyncio.run(agent.plan_research(research_state))

    assert "args" in prompt_called
    ir, ihf, hf, ms = prompt_called["args"]
    assert ir == research_state["initial_research"]
    assert ihf is False
    assert hf is None
    assert ms == research_state["task"]["max_sections"]

    assert printed["agent"] == "EDITOR"

    assert result["title"] is None
    assert result["date"] is None
    assert result["sections"] == []
