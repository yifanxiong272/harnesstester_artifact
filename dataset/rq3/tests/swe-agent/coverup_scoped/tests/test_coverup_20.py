# file: sweagent/agent/agents.py:581-615
# asked: {"lines": [584, 585, 591, 597, 598, 599, 600], "branches": [[583, 584], [590, 591], [595, 597], [597, 0], [597, 598], [598, 597], [598, 599]]}
# gained: {"lines": [584, 585, 591, 597, 598, 599, 600], "branches": [[583, 584], [590, 591], [595, 597], [597, 0], [597, 598], [598, 597], [598, 599]]}

import json
from types import SimpleNamespace, MethodType
from pathlib import Path

import pytest
import yaml

from sweagent.agent.agents import DefaultAgent


class DummyLogger:
    def __init__(self):
        self.infos = []

    def info(self, msg):
        self.infos.append(msg)


class DummySelf:
    def __init__(self):
        self.templates = SimpleNamespace(demonstration_template=None, put_demos_in_history=False)
        self.logger = DummyLogger()
        self.name = "dummy-agent"
        self.appended = []

    def _append_history(self, entry):
        # append a shallow copy to simulate realistic behavior
        self.appended.append(dict(entry))


def test_add_demonstration_raises_when_no_template_and_not_putting_in_history():
    dummy = DummySelf()
    dummy.templates.demonstration_template = None
    dummy.templates.put_demos_in_history = False

    # Bind the unbound function to our dummy object and call it.
    func = MethodType(DefaultAgent._add_demonstration_to_history, dummy)

    # The check and ValueError happen before any file IO, so the path can be anything.
    with pytest.raises(ValueError) as excinfo:
        func(Path("does_not_matter.json"))
    assert "Cannot use demonstrations without a demonstration template or put_demos_in_history=True" in str(
        excinfo.value
    )


def test_add_demonstration_reads_yaml_and_puts_each_demo_in_history(tmp_path):
    # Create YAML demonstration with a system message and two other roles
    demo = {
        "history": [
            {"role": "system", "content": "system message"},
            {"role": "user", "content": "user message"},
            {"role": "assistant", "content": "assistant message"},
        ]
    }
    demo_path = tmp_path / "demo.yaml"
    demo_path.write_text(yaml.safe_dump(demo))

    dummy = DummySelf()
    # Enable putting demos in history so the loop branch is taken
    dummy.templates.put_demos_in_history = True
    dummy.templates.demonstration_template = None

    func = MethodType(DefaultAgent._add_demonstration_to_history, dummy)
    func(demo_path)

    # The system message should be skipped; two entries appended
    assert len(dummy.appended) == 2
    roles = [e["role"] for e in dummy.appended]
    assert roles == ["user", "assistant"]
    # Each appended entry must have is_demo True and original content preserved
    contents = [e["content"] for e in dummy.appended]
    assert contents == ["user message", "assistant message"]
    for entry in dummy.appended:
        assert entry.get("is_demo") is True


def test_add_demonstration_renders_template_and_appends_single_message_for_json(tmp_path):
    # JSON demo with a system message and two other roles
    demo = {
        "history": [
            {"role": "system", "content": "system secret"},
            {"role": "user", "content": "first user line"},
            {"role": "assistant", "content": "assistant reply"},
        ]
    }
    demo_path = tmp_path / "demo.json"
    demo_path.write_text(json.dumps(demo))

    dummy = DummySelf()
    # Use a demonstration template and do not put demos directly into history
    dummy.templates.put_demos_in_history = False
    dummy.templates.demonstration_template = "DEMO BEGIN\n{{ demonstration }}\nDEMO END"

    func = MethodType(DefaultAgent._add_demonstration_to_history, dummy)
    func(demo_path)

    # Expect exactly one appended entry with the rendered demonstration
    assert len(dummy.appended) == 1
    entry = dummy.appended[0]
    assert entry["agent"] == dummy.name
    # system message should be removed; remaining contents concatenated with newline
    expected_demo_message = "first user line\nassistant reply"
    expected_rendered = f"DEMO BEGIN\n{expected_demo_message}\nDEMO END"
    assert entry["content"] == expected_rendered
    assert entry["is_demo"] is True
    assert entry["role"] == "user"
    assert entry["message_type"] == "demonstration"
