# file: multi_agents_ag2/agents/editor.py:65-89
# asked: {"lines": [65, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 79, 80, 81, 84, 87], "branches": []}
# gained: {"lines": [65, 72, 73, 74, 75, 76, 79, 80, 81, 84, 87], "branches": []}

import importlib
import importlib.util
from pathlib import Path
import sys
import types

import pytest


def import_editor_module():
    """
    Try to import the editor module by package name first; if that fails,
    try several plausible filesystem locations relative to the current working directory.
    """
    module_name = "gpt_researcher.multi_agents_ag2.agents.editor"
    try:
        return importlib.import_module(module_name)
    except Exception:
        pass

    # Candidate relative paths where the file might live
    candidates = [
        Path.cwd() / "gpt_researcher" / "multi_agents_ag2" / "agents" / "editor.py",
        Path.cwd() / "gpt-researcher" / "multi_agents_ag2" / "agents" / "editor.py",
        Path.cwd() / "multi_agents_ag2" / "agents" / "editor.py",
        # Also support repository layouts where tests run from inside the package directory
        Path(__file__).resolve().parent / "gpt_researcher" / "multi_agents_ag2" / "agents" / "editor.py",
        Path(__file__).resolve().parent / "gpt-researcher" / "multi_agents_ag2" / "agents" / "editor.py",
    ]

    for p in candidates:
        if p.exists():
            spec = importlib.util.spec_from_file_location("test_loaded_editor", str(p))
            module = importlib.util.module_from_spec(spec)
            # Insert the module into sys.modules to behave like a normal import
            sys.modules["test_loaded_editor"] = module
            loader = spec.loader
            if loader is None:
                raise ImportError(f"No loader for spec {spec}")
            loader.exec_module(module)
            return module

    raise ModuleNotFoundError(
        "Could not locate editor.py in expected locations. Tried package import and filesystem candidates."
    )


class DummyDateTime:
    @classmethod
    def now(cls):
        return cls()

    def strftime(self, fmt):
        return "01/01/2000"


def test_format_planning_instructions_includes_feedback(monkeypatch):
    editor_module = import_editor_module()

    # Patch the module-level datetime name (module likely uses `from datetime import datetime`).
    monkeypatch.setattr(editor_module, "datetime", DummyDateTime)

    agent = editor_module.EditorAgent()

    initial_research = "This is a short research summary."
    include_human_feedback = True
    human_feedback = "Please emphasize experimental results"
    max_sections = 4

    result = agent._format_planning_instructions(
        initial_research=initial_research,
        include_human_feedback=include_human_feedback,
        human_feedback=human_feedback,
        max_sections=max_sections,
    )

    # Check that the fixed date appears
    assert "Today's date is 01/01/2000" in result
    # Check research summary is included
    assert f"Research summary report: '{initial_research}'" in result
    # Check the feedback instruction is included when conditions are met
    expected_feedback_snippet = (
        f"Human feedback: {human_feedback}. You must plan the sections based on the human feedback."
    )
    assert expected_feedback_snippet in result
    # Check max sections instruction is present
    assert f"You must generate a maximum of {max_sections} section headers." in result
    # Check that the JSON format instruction mention is present
    assert "'sections' (maximum" in result


@pytest.mark.parametrize("human_feedback", ["no", "", None])
def test_format_planning_instructions_excludes_feedback_variants(monkeypatch, human_feedback):
    editor_module = import_editor_module()
    monkeypatch.setattr(editor_module, "datetime", DummyDateTime)

    agent = editor_module.EditorAgent()

    initial_research = "Another research summary."
    include_human_feedback = True
    max_sections = 2

    result = agent._format_planning_instructions(
        initial_research=initial_research,
        include_human_feedback=include_human_feedback,
        human_feedback=human_feedback,
        max_sections=max_sections,
    )

    # Date and research summary should still be present
    assert "Today's date is 01/01/2000" in result
    assert f"Research summary report: '{initial_research}'" in result
    # When human_feedback is "no", empty, or None, the feedback instruction must not appear
    assert "Human feedback:" not in result
    # Ensure max sections instruction still present
    assert f"You must generate a maximum of {max_sections} section headers." in result


def test_format_planning_instructions_ignores_feedback_when_flag_false(monkeypatch):
    editor_module = import_editor_module()
    monkeypatch.setattr(editor_module, "datetime", DummyDateTime)

    agent = editor_module.EditorAgent()

    initial_research = "Ignored feedback summary."
    include_human_feedback = False
    human_feedback = "This should be ignored"
    max_sections = 5

    result = agent._format_planning_instructions(
        initial_research=initial_research,
        include_human_feedback=include_human_feedback,
        human_feedback=human_feedback,
        max_sections=max_sections,
    )

    assert "Human feedback:" not in result
    assert f"You must generate a maximum of {max_sections} section headers." in result
    assert "Today's date is 01/01/2000" in result
