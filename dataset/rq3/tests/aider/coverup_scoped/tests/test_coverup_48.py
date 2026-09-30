# file: aider/gui.py:219-240
# asked: {"lines": [219, 220, 221, 222, 225, 226, 227, 228, 229, 230, 233, 234, 235, 236, 237, 239], "branches": []}
# gained: {"lines": [219, 220, 221, 222, 225, 226, 227, 228, 229, 230, 233, 234, 235, 236, 237, 239], "branches": []}

import types
import pytest

import aider.gui as gui_module
from aider.gui import GUI


class FakePopoverCM:
    def __init__(self, label, recorder):
        self.label = label
        self.recorder = recorder

    def __enter__(self):
        self.recorder['popover_entered'] = True
        self.recorder['popover_label'] = self.label
        return None

    def __exit__(self, exc_type, exc, tb):
        self.recorder['popover_exited'] = True
        return False


class FakeStreamlit:
    def __init__(self, recorder):
        self._rec = recorder

    def popover(self, label):
        return FakePopoverCM(label, self._rec)

    def markdown(self, *args, **kwargs):
        self._rec['markdown_called'] = True
        self._rec['markdown_args'] = args
        self._rec['markdown_kwargs'] = kwargs

    def text_input(self, *args, **kwargs):
        self._rec['text_input_called'] = True
        self._rec['text_input_args'] = args
        self._rec['text_input_kwargs'] = kwargs
        return "fake-text"

    def radio(self, *args, **kwargs):
        self._rec['radio_called'] = True
        self._rec['radio_args'] = args
        self._rec['radio_kwargs'] = kwargs
        return args[1][0] if len(args) > 1 and isinstance(args[1], (list, tuple)) else None

    def selectbox(self, *args, **kwargs):
        self._rec['selectbox_called'] = True
        self._rec['selectbox_args'] = args
        self._rec['selectbox_kwargs'] = kwargs
        if len(args) > 1 and isinstance(args[1], (list, tuple)) and args[1]:
            return args[1][0]
        return None


@pytest.fixture
def recorder():
    return {}


def setup_fake_st(monkeypatch, recorder):
    fake_st = FakeStreamlit(recorder)
    monkeypatch.setattr(gui_module, "st", fake_st)
    return fake_st


def make_minimal_gui_instance():
    # Create an instance without running __init__
    g = GUI.__new__(GUI)
    # Attach any attributes that might be referenced elsewhere defensively
    g.prompt = None
    g.prompt_as = 'user'
    g.last_undo_empty = None
    g.recent_msgs_empty = None
    g.web_content_empty = None
    return g


def test_do_run_shell_when_prompt_not_pending(monkeypatch, recorder):
    """
    Call do_run_shell on a minimally-constructed GUI instance where prompt_pending() is False.
    Verify streamlit functions were invoked and selectbox disabled is False.
    """
    setup_fake_st(monkeypatch, recorder)

    g = make_minimal_gui_instance()
    # Bind an instance-level prompt_pending that returns False
    g.prompt_pending = types.MethodType(lambda self: False, g)

    # Call the method under test
    result = GUI.do_run_shell(g)

    assert result is None

    assert recorder.get("popover_entered") is True
    assert recorder.get("popover_exited") is True
    assert recorder.get("popover_label") == "Run shell commands, tests, etc"

    assert recorder.get("markdown_called") is True
    assert "Run a shell command" in recorder.get("markdown_args")[0]

    assert recorder.get("text_input_called") is True
    assert recorder.get("radio_called") is True

    assert recorder.get("selectbox_called") is True
    assert recorder["selectbox_args"][0] == "Recent commands"
    assert "my_app.py --doit" in recorder["selectbox_args"][1]
    assert recorder["selectbox_kwargs"].get("disabled") is False


def test_do_run_shell_when_prompt_pending(monkeypatch, recorder):
    """
    Call do_run_shell on a minimally-constructed GUI instance where prompt_pending() is True.
    Verify selectbox disabled is True.
    """
    setup_fake_st(monkeypatch, recorder)

    g = make_minimal_gui_instance()
    # Bind an instance-level prompt_pending that returns True
    g.prompt_pending = types.MethodType(lambda self: True, g)

    result = GUI.do_run_shell(g)

    assert result is None
    assert recorder.get("selectbox_called") is True
    assert recorder["selectbox_kwargs"].get("disabled") is True
