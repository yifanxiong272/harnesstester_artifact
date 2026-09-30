import json
from pathlib import Path
import pytest

from sweagent.agent import agents
from sweagent.agent.agents import DefaultAgent


class _DummyLogger:
    def info(self, *args, **kwargs):
        # deterministic no-op
        return None


class _Templates:
    def __init__(self, demonstration_template=None, put_demos_in_history=False):
        self.demonstration_template = demonstration_template
        self.put_demos_in_history = put_demos_in_history


def _make_agent():
    # Create an uninitialized DefaultAgent and attach minimal attributes
    agent = object.__new__(DefaultAgent)
    agent.logger = _DummyLogger()
    agent.name = "test-agent"
    # collector for appended history items
    agent._appended = []

    def _append_history(item):
        # append a shallow copy for determinism
        agent._appended.append(dict(item))

    agent._append_history = _append_history
    return agent


def test_missing_template_raises_ValueError_round_038():
    agent = _make_agent()
    # templates with no demonstration template and no put_demos_in_history
    agent.templates = _Templates(demonstration_template=None, put_demos_in_history=False)

    # Use any Path-like object; method should raise before file access
    with pytest.raises(ValueError) as exc:
        agent._add_demonstration_to_history(Path("/does/not/matter.txt"))
    assert "Cannot use demonstrations without a demonstration template or put_demos_in_history=True" in str(exc.value)


def test_yaml_put_demos_in_history_true_round_038(tmp_path):
    agent = _make_agent()
    agent.templates = _Templates(demonstration_template=None, put_demos_in_history=True)

    # Build YAML demo file with a mixture of system and non-system entries
    yaml_text = """
history:
  - role: system
    content: System message
  - role: user
    content: User message 1
  - role: assistant
    content: Assistant message 1
"""
    demo_file = tmp_path / "demo.yaml"
    demo_file.write_text(yaml_text)

    # Call the method under test
    agent._add_demonstration_to_history(demo_file)

    # System role should be skipped; two entries appended and marked as demo
    assert len(agent._appended) == 2
    roles = {entry["role"] for entry in agent._appended}
    assert roles == {"user", "assistant"}
    for entry in agent._appended:
        assert entry.get("is_demo") is True
        # content should be preserved
        assert "message" not in entry or isinstance(entry.get("content"), str)


def test_json_put_demos_in_history_false_uses_template_round_038(tmp_path, monkeypatch):
    agent = _make_agent()
    # demonstration_template provided, put_demos_in_history False -> single rendered message
    agent.templates = _Templates(demonstration_template="TEMPLATE: {{ demonstration }}", put_demos_in_history=False)

    # Patch the Template used in module to a deterministic fake
    class _FakeTemplate:
        def __init__(self, template_text):
            self.template_text = template_text

        def render(self, **kwargs):
            # return a predictable string using the demonstration content
            demo = kwargs.get("demonstration", "")
            return f"RENDERED[{demo}]"

    monkeypatch.setattr(agents, "Template", _FakeTemplate)

    demo_history = {
        "history": [
            {"role": "system", "content": "system message"},
            {"role": "user", "content": "first user line"},
            {"role": "assistant", "content": "assistant line"}
        ]
    }
    demo_file = tmp_path / "demo.json"
    demo_file.write_text(json.dumps(demo_history))

    agent._add_demonstration_to_history(demo_file)

    # Only one message appended (single rendered demonstration)
    assert len(agent._appended) == 1
    appended = agent._appended[0]
    assert appended["agent"] == agent.name
    assert appended["is_demo"] is True
    assert appended["role"] == "user"
    assert appended["message_type"] == "demonstration"
    # The content should be what our fake Template.render produced
    assert appended["content"].startswith("RENDERED[") and "first user line" in appended["content"]
