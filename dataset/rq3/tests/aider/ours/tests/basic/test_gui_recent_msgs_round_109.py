import types
import builtins
import pytest
from types import SimpleNamespace

import aider.gui as gui_mod
from aider.gui import GUI


class FakeEmpty:
    def __init__(self):
        self.empty_called = False
        self.__entered = False

    def empty(self):
        # Simulate Streamlit DeltaGenerator.empty()
        self.empty_called = True

    def __enter__(self):
        self.__entered = True
        return self

    def __exit__(self, exc_type, exc, tb):
        self.__entered = False
        return False


def _make_fake_st(empty_obj, selectbox_func):
    """
    Build a minimal fake `st` module with .empty and .selectbox attributes.
    """
    fake = SimpleNamespace()
    fake.empty = lambda: empty_obj
    fake.selectbox = selectbox_func
    return fake


def test_do_recent_msgs_sets_empty_and_no_prompt_round_109(monkeypatch):
    # Create a GUI *without* running its heavy initializer
    g = object.__new__(GUI)

    # recent_msgs_empty falsy -> should be replaced by st.empty()
    g.recent_msgs_empty = False

    # Minimal state expected by the function
    g.state = SimpleNamespace(recent_msgs_num=42, input_history=["alpha", "beta"])
    # prompt should remain unchanged when selectbox returns None
    g.prompt = "initial"

    # patch prompt_pending to return False to exercise the branch where .empty() is NOT called
    g.prompt_pending = lambda: False

    # Fake st.empty returns our FakeEmpty instance
    fake_empty = FakeEmpty()

    # selectbox should be called but return None (no selection)
    def fake_selectbox(*args, **kwargs):
        # Return None to simulate no selection made by user
        return None

    fake_st = _make_fake_st(fake_empty, fake_selectbox)

    # Patch the st symbol exactly where aider.gui resolves it
    monkeypatch.setattr(gui_mod, "st", fake_st)

    # Run the function under test
    g.do_recent_msgs()

    # Assertions: recent_msgs_empty was replaced with our fake container
    assert g.recent_msgs_empty is fake_empty, "recent_msgs_empty should be set to st.empty() result"

    # old_prompt should be set (assigned inside function) and be None because selectbox returned None
    assert getattr(g, "old_prompt", None) is None

    # prompt should remain unchanged because no old_prompt was provided
    assert g.prompt == "initial"

    # recent_msgs_num should be unchanged because prompt_pending() was False
    assert g.state.recent_msgs_num == 42


def test_do_recent_msgs_uses_existing_and_sets_prompt_round_109(monkeypatch):
    # Create GUI instance without calling __init__
    g = object.__new__(GUI)

    # Provide an existing recent_msgs_empty (truthy) so the branch that sets it to st.empty() is skipped
    fake_empty = FakeEmpty()
    g.recent_msgs_empty = fake_empty

    # state with a known recent_msgs_num to observe increment
    g.state = SimpleNamespace(recent_msgs_num=0, input_history=["one", "two"])

    # initial prompt value to verify it gets overwritten
    g.prompt = None

    # Force prompt_pending True to exercise branch that calls recent_msgs_empty.empty() and increments the counter
    g.prompt_pending = lambda: True

    # We'll capture kwargs passed to selectbox to assert the key reflects incremented recent_msgs_num
    captured = {}

    def fake_selectbox(*args, **kwargs):
        captured['args'] = args
        captured['kwargs'] = kwargs
        # Simulate the user selecting a non-empty previous message
        return "reselected prompt"

    fake_st = _make_fake_st(fake_empty, fake_selectbox)
    monkeypatch.setattr(gui_mod, "st", fake_st)

    # Call the method
    g.do_recent_msgs()

    # Assert the container's empty() was called because prompt_pending() returned True
    assert fake_empty.empty_called is True, "expected recent_msgs_empty.empty() to be called when prompt_pending() is True"

    # recent_msgs_num should have been incremented by 1 before selectbox key is computed
    assert g.state.recent_msgs_num == 1

    # The selectbox should have been called and the returned value assigned
    assert getattr(g, "old_prompt", None) == "reselected prompt"
    assert g.prompt == "reselected prompt"

    # Verify selectbox was passed a key that matches the incremented recent_msgs_num
    assert 'kwargs' in captured, "selectbox should have been called and its kwargs captured"
    key_passed = captured['kwargs'].get('key')
    assert key_passed == f"recent_msgs_{g.state.recent_msgs_num}", (
        f"expected selectbox key to reflect incremented recent_msgs_num; got {key_passed}"
    )
