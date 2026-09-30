import json
from types import SimpleNamespace
from pathlib import Path

import pytest

from sweagent.agent.agents import DefaultAgent


def _make_agent_for_demo_calls():
    """Create a lightweight DefaultAgent instance by bypassing __init__.

    We only attach the attributes used by _add_demonstration_to_history so the
    real heavy initialization is avoided. This keeps tests deterministic and
    isolated.
    """
    agent = object.__new__(DefaultAgent)
    # basic attributes used by _add_demonstration_to_history
    agent.name = "test-agent"
    agent.logger = SimpleNamespace(info=lambda *a, **k: None)
    return agent


def test_raises_when_no_template_and_not_put_demos_in_history_round_040(tmp_path):
    """Cover branch where no demonstration_template and put_demos_in_history is False.

    Expect a ValueError with the exact message from the implementation.
    """
    agent = _make_agent_for_demo_calls()
    # templates must expose demostration_template and put_demos_in_history
    agent.templates = SimpleNamespace(demonstration_template=None, put_demos_in_history=False)
    # _append_history should never be called in this scenario; attach one that would fail
    called = {"flag": False}

    def _bad_append(_):
        called["flag"] = True
        raise AssertionError("_append_history should not be invoked")

    agent._append_history = _bad_append

    demo_path = tmp_path / "any.json"
    demo_path.write_text(json.dumps({"history": []}))

    with pytest.raises(ValueError) as excinfo:
        agent._add_demonstration_to_history(demo_path)

    assert "Cannot use demonstrations without a demonstration template or put_demos_in_history=True" in str(excinfo.value)
    assert called["flag"] is False


def test_adds_each_entry_to_history_round_040(tmp_path):
    """Cover path where put_demos_in_history is True and YAML is used.

    Ensures that system-role entries are skipped and other entries are appended
    individually with is_demo set to True.
    """
    agent = _make_agent_for_demo_calls()
    agent.templates = SimpleNamespace(demonstration_template=None, put_demos_in_history=True)

    appended = []

    def _capture_append(entry):
        # copy to avoid mutation later by reference
        appended.append(dict(entry))

    agent._append_history = _capture_append

    # create a YAML demonstration file with a system entry and a user entry
    yaml_text = (
        "history:\n"
        "  - role: system\n"
        "    content: system-message\n"
        "  - role: user\n"
        "    content: user-message\n"
    )
    demo_path = tmp_path / "demo.yaml"
    demo_path.write_text(yaml_text)

    # Call the method under test
    agent._add_demonstration_to_history(demo_path)

    # Only the non-system entry should be appended, and must have is_demo True
    assert len(appended) == 1, "Expected exactly one appended non-system entry"
    entry = appended[0]
    assert entry.get("role") == "user"
    assert entry.get("content") == "user-message"
    assert entry.get("is_demo") is True


def test_adds_single_message_round_040(tmp_path):
    """Cover path where demonstrations are rendered via a template and appended as a single message.

    Uses a JSON demonstration file. Verifies that system entries are filtered out,
    the remaining contents are joined with newlines, run through the jinja2
    Template, and then _append_history is called with the expected keys and values.
    """
    agent = _make_agent_for_demo_calls()
    # Provide a simple deterministic Jinja template
    agent.templates = SimpleNamespace(demonstration_template="DEMO: {{ demonstration }}", put_demos_in_history=False)

    appended = []

    def _capture_append(entry):
        appended.append(dict(entry))

    agent._append_history = _capture_append

    # JSON demo with a system entry and two non-system entries
    demo_content = {
        "history": [
            {"role": "system", "content": "sys"},
            {"role": "assistant", "content": "assistant-content"},
            {"role": "user", "content": "user-content"},
        ]
    }
    demo_path = tmp_path / "demo.json"
    demo_path.write_text(json.dumps(demo_content))

    agent._add_demonstration_to_history(demo_path)

    # Should have a single appended demonstration message
    assert len(appended) == 1
    msg = appended[0]

    # The template prepends 'DEMO: ' and the demonstration is the joined contents of non-system entries
    expected_demo_text = "assistant-content\nuser-content"
    assert msg.get("content") == f"DEMO: {expected_demo_text}"
    assert msg.get("agent") == agent.name
    assert msg.get("is_demo") is True
    assert msg.get("role") == "user"
    assert msg.get("message_type") == "demonstration"
