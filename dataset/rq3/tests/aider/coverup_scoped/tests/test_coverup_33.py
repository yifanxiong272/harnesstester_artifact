# file: aider/gui.py:280-299
# asked: {"lines": [280, 281, 282, 284, 285, 286, 288, 289, 290, 291, 292, 294, 295, 296, 298, 299], "branches": [[281, 282], [281, 284], [284, 285], [284, 288], [298, 0], [298, 299]]}
# gained: {"lines": [280, 281, 282, 284, 285, 286, 288, 289, 290, 291, 292, 294, 295, 296, 298, 299], "branches": [[281, 282], [284, 285], [284, 288], [298, 0], [298, 299]]}

import types
import pytest

from aider import gui as aider_gui
from aider.gui import GUI


class FakeEmpty:
    def __init__(self):
        self.entered = False
        self.empty_called = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def empty(self):
        self.empty_called = True


class FakeSt:
    def __init__(self, selectbox_return=None):
        self._selectbox_return = selectbox_return
        self.last_selectbox = None
        self.empty_created = []

    def empty(self):
        e = FakeEmpty()
        self.empty_created.append(e)
        return e

    def selectbox(self, *args, **kwargs):
        # record a copy of args/kwargs for assertions
        self.last_selectbox = (args, dict(kwargs))
        return self._selectbox_return


class SimpleState:
    def __init__(self, input_history=None, recent_msgs_num=0):
        self.input_history = input_history if input_history is not None else []
        self.recent_msgs_num = recent_msgs_num


def make_gui_instance():
    # create GUI instance without running __init__
    g = object.__new__(GUI)
    # initialize attributes used by do_recent_msgs
    g.recent_msgs_empty = None
    g.old_prompt = None
    g.prompt = None
    g.state = SimpleState()
    return g


def test_do_recent_msgs_not_pending_select_none(monkeypatch):
    fake_st = FakeSt(selectbox_return=None)
    monkeypatch.setattr(aider_gui, "st", fake_st)

    g = make_gui_instance()
    # prepare input history and ensure prompt_pending returns False
    g.state.input_history = ["one", "two", "three"]
    g.state.recent_msgs_num = 2
    g.prompt_pending = lambda: False

    # Call method
    g.do_recent_msgs()

    # After call, recent_msgs_empty should be set to a FakeEmpty and entered via context
    assert isinstance(g.recent_msgs_empty, FakeEmpty)
    # selectbox should have been called once with expected first two positional args
    assert fake_st.last_selectbox is not None
    (args, kwargs) = fake_st.last_selectbox
    assert args[0] == "Resend a recent chat message"
    assert args[1] is g.state.input_history
    # placeholder and key should be present
    assert "placeholder" in kwargs and kwargs["placeholder"].startswith("Choose")
    assert "key" in kwargs and kwargs["key"] == f"recent_msgs_{g.state.recent_msgs_num}"
    # disabled should be False because prompt_pending returned False
    assert "disabled" in kwargs and kwargs["disabled"] is False
    # Since selectbox returned None, old_prompt and prompt should remain falsy
    assert g.old_prompt is None
    assert g.prompt is None
    # recent_msgs_num must be unchanged
    assert g.state.recent_msgs_num == 2


def test_do_recent_msgs_pending_and_select_sets_prompt(monkeypatch):
    fake_st = FakeSt(selectbox_return="resend this")
    monkeypatch.setattr(aider_gui, "st", fake_st)

    g = make_gui_instance()
    g.state.input_history = ["alpha", "beta"]
    g.state.recent_msgs_num = 5

    # prompt_pending returns True to exercise branch that calls .empty() and increments counter
    g.prompt_pending = lambda: True

    # Call method
    g.do_recent_msgs()

    # recent_msgs_empty should be a FakeEmpty and its empty() should have been called
    assert isinstance(g.recent_msgs_empty, FakeEmpty)
    assert g.recent_msgs_empty.empty_called is True

    # recent_msgs_num should have been incremented by 1 before building the selectbox key
    assert g.state.recent_msgs_num == 6

    # selectbox should have been called and disabled True
    (args, kwargs) = fake_st.last_selectbox
    assert kwargs["disabled"] is True
    assert kwargs["key"] == "recent_msgs_6"

    # old_prompt and prompt should be set to the value returned by selectbox
    assert g.old_prompt == "resend this"
    assert g.prompt == "resend this"
