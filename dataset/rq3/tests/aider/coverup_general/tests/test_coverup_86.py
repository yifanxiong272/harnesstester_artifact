# file: aider/gui.py:262-278
# asked: {"lines": [262, 263, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 277], "branches": []}
# gained: {"lines": [262, 263, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 277], "branches": []}

import pytest

def _make_dummy_cm(calls, name):
    class DummyCM:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            calls.setdefault(f"{name}_init", []).append((args, kwargs))
        def __enter__(self):
            calls.setdefault("entered", 0)
            calls["entered"] += 1
            calls.setdefault(f"{name}_enter", []).append((self.args, self.kwargs))
            return self
        def __exit__(self, exc_type, exc, tb):
            calls.setdefault("exited", 0)
            calls["exited"] += 1
            calls.setdefault(f"{name}_exit", []).append((exc_type, exc, tb))
            return False
    return DummyCM

def _patch_streamlit_for_tests(monkeypatch, gui_mod, calls):
    # Patch expander and popover to be simple context managers that record usage.
    monkeypatch.setattr(gui_mod.st, "expander", lambda *args, **kwargs: _make_dummy_cm(calls, "expander")(*args, **kwargs))
    monkeypatch.setattr(gui_mod.st, "popover", lambda *args, **kwargs: _make_dummy_cm(calls, "popover")(*args, **kwargs))

    # Patch markdown, text_input, selectbox to record their calls.
    def fake_markdown(text):
        calls.setdefault("markdown", []).append(text)
        return None
    def fake_text_input(label, value=None, **kwargs):
        calls.setdefault("text_input", []).append((label, value, kwargs))
        return value
    def fake_selectbox(label, options, **kwargs):
        calls.setdefault("selectbox", []).append((label, tuple(options), kwargs))
        # Return first option to mimic a selection
        return options[0] if options else None

    monkeypatch.setattr(gui_mod.st, "markdown", fake_markdown)
    monkeypatch.setattr(gui_mod.st, "text_input", fake_text_input)
    monkeypatch.setattr(gui_mod.st, "selectbox", fake_selectbox)

@pytest.mark.parametrize("prompt_pending_value", [False, True])
def test_do_git_selectbox_disabled_branch(monkeypatch, prompt_pending_value):
    """
    Exercises GUI.do_git to hit the code under the st.expander and st.popover,
    and asserts that the selectbox received the correct disabled flag according
    to prompt_pending().
    """
    import aider.gui as gui_mod

    calls = {}
    _patch_streamlit_for_tests(monkeypatch, gui_mod, calls)

    # Record button presses by patching GUI.button
    def fake_button(self, label):
        calls.setdefault("buttons", []).append(label)
        return True
    monkeypatch.setattr(gui_mod.GUI, "button", fake_button)

    # Instead of calling __init__ (which would call get_coder and trigger CLI parsing),
    # construct the GUI instance without running __init__ to avoid side effects.
    gui = object.__new__(gui_mod.GUI)

    # Attach a prompt_pending method to the instance to control the disabled flag.
    gui.prompt_pending = lambda: prompt_pending_value

    # Call the method under test
    gui.do_git()

    # Assertions: buttons were called for commit and run
    assert "buttons" in calls, "GUI.button was not called"
    assert "Commit any pending changes" in calls["buttons"], "Commit button not called"
    assert "Run" in calls["buttons"], "Run button not called"

    # Assertions: markdown and text_input called
    assert calls.get("markdown") == ["## Run git command"]
    assert calls.get("text_input"), "text_input was not called"
    label, value, kwargs = calls["text_input"][-1]
    assert label == "git"
    assert value == "git "

    # Assertions: selectbox called and disabled kwarg matches prompt_pending_value
    assert calls.get("selectbox"), "selectbox was not called"
    sel_label, sel_options, sel_kwargs = calls["selectbox"][-1]
    assert sel_label == "Recent git commands"
    assert sel_options == ("git checkout -b experiment", "git stash")
    # The code passes disabled=self.prompt_pending()
    assert sel_kwargs.get("disabled") is prompt_pending_value

    # Context managers should have been entered twice (expander + popover) and exited twice
    assert calls.get("entered", 0) == 2
    assert calls.get("exited", 0) == 2
