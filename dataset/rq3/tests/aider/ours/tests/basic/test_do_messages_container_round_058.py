import types
import pytest
from types import SimpleNamespace

import aider.gui as gui_mod
from aider.gui import GUI


def test_do_messages_container_round_058(monkeypatch):
    """
    Exercise GUI.do_messages_container for all message-role branches:
    - 'edit' -> calls show_edit_info
    - 'info' -> calls st.info
    - 'text' -> uses expander and calls st.text with full text
    - 'user' and 'assistant' -> enters chat_message and calls st.write
    - unknown role -> calls st.dict with the full message dict

    This test patches aider.gui.st with a deterministic fake implementation
    that records observable calls so we can assert precise behavior.
    """

    calls = []

    class FakeExpander:
        def __init__(self, parent, label):
            self.parent = parent
            self.label = label

        def __enter__(self):
            # record that an expander was entered with this label
            calls.append(("expander_enter", self.label))
            return self

        def __exit__(self, exc_type, exc, tb):
            calls.append(("expander_exit", self.label))
            return False

    class FakeChatMessage:
        def __init__(self, parent, role):
            self.parent = parent
            self.role = role

        def __enter__(self):
            calls.append(("chat_enter", self.role))
            return self

        def __exit__(self, exc_type, exc, tb):
            calls.append(("chat_exit", self.role))
            return False

    class FakeContainer:
        def __init__(self, parent):
            self.parent = parent

        def __enter__(self):
            calls.append(("container_enter", True))
            return self

        def __exit__(self, exc_type, exc, tb):
            calls.append(("container_exit", True))
            return False

        def expander(self, label):
            # return a context manager that records enter/exit
            return FakeExpander(self, label)

    class FakeST:
        def container(self):
            return FakeContainer(self)

        def info(self, value):
            calls.append(("info", value))

        def text(self, value):
            calls.append(("text", value))

        def write(self, value):
            calls.append(("write", value))

        def dict(self, value):
            calls.append(("dict", value))

        def chat_message(self, role):
            return FakeChatMessage(self, role)

    fake_st = FakeST()

    # Patch the st object used by the module under test
    monkeypatch.setattr(gui_mod, "st", fake_st)

    # Create a GUI instance without running __init__ (avoid heavy init)
    g = object.__new__(GUI)

    # Prepare a capture for calls to show_edit_info
    show_edit_calls = []

    def fake_show_edit_info(msg):
        show_edit_calls.append(msg)

    g.show_edit_info = fake_show_edit_info

    # Compose a set of messages to hit each branch
    multiline = "First line\nsecond line\nthird"
    mystery_msg = {"role": "mystery", "content": {"a": 1}}
    g.state = SimpleNamespace(messages=[
        {"role": "edit", "content": "edit content", "meta": 1},
        {"role": "info", "content": "some info"},
        {"role": "text", "content": multiline},
        {"role": "user", "content": "user said hello"},
        {"role": "assistant", "content": "assistant reply"},
        mystery_msg,
    ])

    # Call the method under test
    g.do_messages_container()

    # Assertions: verify each branch produced the expected observable calls
    # 1) show_edit_info for the 'edit' message
    assert len(show_edit_calls) == 1
    assert show_edit_calls[0]["role"] == "edit"
    assert show_edit_calls[0]["content"] == "edit content"

    # 2) st.info called with the 'info' content
    assert ("info", "some info") in calls

    # 3) 'text' branch: expander entered with first line and st.text called with full multiline
    first_line = multiline.splitlines()[0]
    assert ("expander_enter", first_line) in calls
    assert ("text", multiline) in calls

    # 4) 'user' and 'assistant' chat_message contexts and write calls
    assert ("chat_enter", "user") in calls
    assert ("write", "user said hello") in calls
    assert ("chat_enter", "assistant") in calls
    assert ("write", "assistant reply") in calls

    # 5) unknown role triggers st.dict with the full message dict (role + content)
    assert ("dict", mystery_msg) in calls

    # 6) container context used at least once
    assert ("container_enter", True) in calls


if __name__ == "__main__":
    pytest.main([__file__])
