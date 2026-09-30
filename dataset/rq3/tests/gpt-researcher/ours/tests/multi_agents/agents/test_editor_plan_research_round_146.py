import asyncio
import pytest

from multi_agents.agents import editor as editor_mod
from multi_agents.agents.editor import EditorAgent


@pytest.mark.asyncio
async def test_plan_research_with_human_feedback_round_146(monkeypatch):
    # Arrange: create instance without running __init__ and inject a prompt builder that
    # expects (initial_research, include_human_feedback, human_feedback, max_sections)
    inst = object.__new__(EditorAgent)

    captured = {}

    def fake_create_prompt(initial_research, include_human_feedback, human_feedback, max_sections):
        # capture values for assertions
        captured['initial_research'] = initial_research
        captured['include_human_feedback'] = include_human_feedback
        captured['human_feedback'] = human_feedback
        captured['max_sections'] = max_sections
        return "PROMPT"

    # assign as instance attribute (will be called as a plain callable)
    inst._create_planning_prompt = fake_create_prompt

    # Patch print_agent_output to capture calls
    printed = {}

    def fake_print_agent_output(message, agent=None):
        printed['message'] = message
        printed['agent'] = agent

    monkeypatch.setattr(editor_mod, 'print_agent_output', fake_print_agent_output)

    # Patch call_model to validate received kwargs and return a deterministic plan
    async def fake_call_model(*, prompt, model, response_format):
        # ensure model and response_format are forwarded
        assert prompt == "PROMPT"
        assert response_format == "json"
        # return a dict resembling the expected model output
        return {
            'title': 'Test Title',
            'date': '2026-01-01',
            'sections': ['Intro', 'Methods', 'Conclusion']
        }

    monkeypatch.setattr(editor_mod, 'call_model', fake_call_model)

    # Prepare research_state containing initial_research, task, human_feedback
    research_state = {
        'initial_research': {'notes': 'some facts'},
        'human_feedback': {'comment': 'please expand methods'},
        'task': {
            'include_human_feedback': True,
            'max_sections': 3,
            'model': 'fake-model'
        }
    }

    # Act
    result = await EditorAgent.plan_research(inst, research_state)

    # Assert: prompt builder received expected values
    assert captured['initial_research'] == research_state['initial_research']
    assert captured['include_human_feedback'] is True
    assert captured['human_feedback'] == research_state['human_feedback']
    assert captured['max_sections'] == research_state['task']['max_sections']

    # print_agent_output was called with expected message and agent tag
    assert printed['agent'] == 'EDITOR'
    assert 'Planning an outline layout' in printed['message']

    # The returned result should reflect the fake model output
    assert result == {
        'title': 'Test Title',
        'date': '2026-01-01',
        'sections': ['Intro', 'Methods', 'Conclusion']
    }


@pytest.mark.asyncio
async def test_plan_research_without_human_feedback_round_146(monkeypatch):
    # Arrange: bypass __init__ and inject a prompt builder to capture calls
    inst = object.__new__(EditorAgent)

    captured = {}

    def fake_create_prompt(initial_research, include_human_feedback, human_feedback, max_sections):
        captured['initial_research'] = initial_research
        captured['include_human_feedback'] = include_human_feedback
        captured['human_feedback'] = human_feedback
        captured['max_sections'] = max_sections
        # vary the prompt to ensure call_model receives it
        return f"PROMPT_NO_HF_{max_sections}"

    inst._create_planning_prompt = fake_create_prompt

    # capture print_agent_output calls
    printed = {}

    def fake_print_agent_output(message, agent=None):
        printed['message'] = message
        printed['agent'] = agent

    monkeypatch.setattr(editor_mod, 'print_agent_output', fake_print_agent_output)

    # Patch call_model to verify prompt and return a different plan
    async def fake_call_model(*, prompt, model, response_format):
        assert prompt.startswith("PROMPT_NO_HF_")
        assert model == 'another-model'
        assert response_format == 'json'
        return {
            'title': 'No HF Title',
            'date': '2026-12-31',
            'sections': []
        }

    monkeypatch.setattr(editor_mod, 'call_model', fake_call_model)

    # Provide research_state with include_human_feedback False and human_feedback present (should be ignored)
    research_state = {
        'initial_research': {'notes': 'other facts'},
        'human_feedback': {'comment': 'this should not be used'},
        'task': {
            'include_human_feedback': False,
            'max_sections': 0,
            'model': 'another-model'
        }
    }

    # Act
    result = await EditorAgent.plan_research(inst, research_state)

    # Assert: prompt builder got the flags correctly
    assert captured['include_human_feedback'] is False
    assert captured['human_feedback'] == research_state['human_feedback']
    assert captured['max_sections'] == 0

    # print_agent_output called appropriately
    assert printed['agent'] == 'EDITOR'
    assert 'Planning an outline layout' in printed['message']

    # result mirrors the fake call_model output
    assert result['title'] == 'No HF Title'
    assert result['sections'] == []
