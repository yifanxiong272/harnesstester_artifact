# file: aider/io.py:400-433
# asked: {"lines": [416, 418, 420, 425, 427, 429, 430], "branches": [[405, 414], [415, 416], [417, 418], [419, 420], [424, 425], [426, 427], [428, 429]]}
# gained: {"lines": [416, 418, 420, 425, 427, 429, 430], "branches": [[405, 414], [415, 416], [417, 418], [419, 420], [424, 425], [426, 427], [428, 429]]}

import pytest
import aider.io as aio


def _patch_style_from_dict(monkeypatch):
    # Replace Style.from_dict used inside aider.io with a classmethod that returns the raw dict.
    # Use classmethod signature to match the original call Style.from_dict(style_dict).
    monkeypatch.setattr(aio.Style, "from_dict", classmethod(lambda cls, d: d))


def _make_instance():
    # Avoid running any InputOutput.__init__ by creating instance via __new__
    inst = object.__new__(aio.InputOutput)
    return inst


def test_get_style_with_user_input_and_completion(monkeypatch):
    _patch_style_from_dict(monkeypatch)

    inst = _make_instance()
    # Configure attributes to exercise the user_input_color branch and completion menu branches
    inst.pretty = True
    inst.user_input_color = "ansiblue"
    inst.completion_menu_bg_color = "red"
    inst.completion_menu_color = "yellow"
    inst.completion_menu_current_bg_color = "green"
    inst.completion_menu_current_color = "magenta"

    style_dict = inst._get_style()

    # Verify the returned object is the dict we expected (from our patched from_dict)
    assert isinstance(style_dict, dict)

    # Verify user input style entries were added
    assert "" in style_dict
    assert style_dict[""] == "ansiblue"
    assert style_dict["pygments.literal.string"] == "bold italic ansiblue"

    # Verify completion-menu style assembled in correct order and format
    assert "completion-menu" in style_dict
    assert style_dict["completion-menu"] == "bg:red yellow"

    # Verify current completion menu style assembled correctly
    assert "completion-menu.completion.current" in style_dict
    assert style_dict["completion-menu.completion.current"] == "green bg:magenta"


def test_get_style_without_user_input_but_completion(monkeypatch):
    _patch_style_from_dict(monkeypatch)

    inst = _make_instance()
    # pretty True so we don't hit the early return; user_input_color falsy to take the 405->414 branch
    inst.pretty = True
    inst.user_input_color = None  # falsy
    inst.completion_menu_bg_color = "red"
    inst.completion_menu_color = "yellow"
    inst.completion_menu_current_bg_color = "green"
    inst.completion_menu_current_color = "magenta"

    style_dict = inst._get_style()

    # Ensure user input keys are not present
    assert "" not in style_dict
    assert "pygments.literal.string" not in style_dict

    # Completion entries should still be present
    assert style_dict["completion-menu"] == "bg:red yellow"
    assert style_dict["completion-menu.completion.current"] == "green bg:magenta"
