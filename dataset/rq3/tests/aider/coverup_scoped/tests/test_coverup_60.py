# file: aider/gui.py:262-278
# asked: {"lines": [262, 263, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 277], "branches": []}
# gained: {"lines": [262, 263, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 277], "branches": []}

import importlib
import sys
import types

import aider.gui as real_gui  # import name so tests can reference module path
import pytest


class _DummyCM:
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    def __enter__(self):
        self.calls.append(f"enter {self.name}")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.calls.append(f"exit {self.name}")


def _make_fake_streamlit(calls):
    """
    Create a fake streamlit module that records calls into the provided list.
    """
    mod = types.ModuleType("streamlit")

    def expander(label, expanded=False):
        return _DummyCM(f"expander:{label}:{expanded}", calls)

    def popover(label):
        return _DummyCM(f"popover:{label}", calls)

    def markdown(text):
        calls.append(("markdown", text))

    def text_input(label, value=None):
        calls.append(("text_input", label, value))
        return value

    def selectbox(label, options, disabled=False):
        calls.append(("selectbox", label, tuple(options), disabled))
        return options[0] if options else None

    # Provide cache_resource decorator used at module import time by aider.gui
    def cache_resource(func=None):
        if func is None:
            # decorator used with args, return a decorator that returns the function unchanged
            def _decorator(f):
                return f
            return _decorator
        return func

    mod.expander = expander
    mod.popover = popover
    mod.markdown = markdown
    mod.text_input = text_input
    mod.selectbox = selectbox
    mod.cache_resource = cache_resource

    return mod


def _reload_gui_with_fake_st(monkeypatch, calls):
    """
    Insert fake streamlit module and reload aider.gui so that its 'st' points to the fake.
    Returns the reloaded module.
    """
    fake_st = _make_fake_streamlit(calls)
    # Ensure fake streamlit is available for import and used by aider.gui
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    # Reload the aider.gui module so it binds to the fake streamlit
    reloaded = importlib.reload(real_gui)
    return reloaded


def _make_instance_with_hooks(GUI_cls, button_calls, prompt_value):
    """
    Create an instance of GUI without running its __init__, attach button and prompt_pending.
    """
    inst = object.__new__(GUI_cls)

    def button(label):
        button_calls.append(label)
        return None

    inst.button = button
    inst.prompt_pending = lambda: prompt_value
    return inst


def test_do_git_with_prompt_pending_false(monkeypatch):
    calls = []
    gui_module = _reload_gui_with_fake_st(monkeypatch, calls)
    GUI = gui_module.GUI

    button_calls = []
    inst = _make_instance_with_hooks(GUI, button_calls, prompt_value=False)

    # Execute the method under test
    inst.do_git()

    # Verify buttons were invoked for "Commit any pending changes" and "Run"
    assert button_calls[:2] == ["Commit any pending changes", "Run"]

    # Verify streamlit context managers were entered and exited in expected order
    assert any(isinstance(entry, str) and entry.startswith("enter expander:Git:False") for entry in calls)
    assert any(isinstance(entry, str) and entry.startswith("enter popover:Run git command") for entry in calls)
    assert any(isinstance(entry, str) and entry.startswith("exit popover:Run git command") for entry in calls)
    assert any(isinstance(entry, str) and entry.startswith("exit expander:Git:False") for entry in calls)

    # Verify markdown and text_input were called
    assert ("markdown", "## Run git command") in calls
    assert ("text_input", "git", "git ") in calls

    # Verify selectbox call recorded and disabled matches prompt_pending (False)
    select_calls = [c for c in calls if isinstance(c, tuple) and c[0] == "selectbox"]
    assert len(select_calls) == 1
    _, label, options, disabled = select_calls[0]
    assert label == "Recent git commands"
    assert options == ("git checkout -b experiment", "git stash")
    assert disabled is False


def test_do_git_with_prompt_pending_true(monkeypatch):
    calls = []
    gui_module = _reload_gui_with_fake_st(monkeypatch, calls)
    GUI = gui_module.GUI

    button_calls = []
    inst = _make_instance_with_hooks(GUI, button_calls, prompt_value=True)

    # Execute the method under test
    inst.do_git()

    # Buttons still called; Run should be attempted even if prompt_pending is True
    assert button_calls[:2] == ["Commit any pending changes", "Run"]

    # Verify selectbox disabled reflects prompt_pending=True
    select_calls = [c for c in calls if isinstance(c, tuple) and c[0] == "selectbox"]
    assert len(select_calls) == 1
    _, label, options, disabled = select_calls[0]
    assert label == "Recent git commands"
    assert options == ("git checkout -b experiment", "git stash")
    assert disabled is True
