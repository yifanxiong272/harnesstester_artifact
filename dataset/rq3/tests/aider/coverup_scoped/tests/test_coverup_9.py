# file: aider/gui.py:360-403
# asked: {"lines": [360, 361, 362, 365, 366, 367, 369, 371, 372, 374, 375, 376, 378, 379, 381, 382, 384, 386, 387, 389, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 403], "branches": [[375, 376], [375, 378], [378, 379], [378, 381], [381, 382], [381, 384], [386, 387], [386, 389], [391, 392], [391, 393], [393, 394], [393, 396], [396, 397], [396, 403]]}
# gained: {"lines": [360, 361, 362, 365, 366, 367, 369, 371, 372, 374, 375, 376, 378, 381, 384, 386, 387, 389, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 403], "branches": [[375, 376], [378, 381], [381, 384], [386, 387], [386, 389], [391, 392], [393, 394], [393, 396], [396, 397]]}

import contextlib
import types
import pytest

import aider.gui as gui_mod


class FakeIO:
    def __init__(self):
        self.history = []

    def add_to_input_history(self, s):
        self.history.append(s)


class FakeCoder:
    def __init__(self):
        self.yield_stream = False
        self.stream = False
        self.pretty = True
        self.io = FakeIO()


class FakeState:
    def __init__(self):
        self.input_history = []
        self.messages = []
        self.prompt = None


class EnterTracker:
    def __init__(self, record_list, label_expected=None):
        self.record_list = record_list
        self.label_expected = label_expected

    def __enter__(self):
        self.record_list.append(("entered", self.label_expected))
        return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.record_list.append(("exited", self.label_expected))
        return False


class FakeMessages:
    def __init__(self, record_list):
        self._record = record_list

    def chat_message(self, label):
        # Return a context manager that records the label
        return EnterTracker(self._record, ("chat_message", label))

    def expander(self, label):
        return EnterTracker(self._record, ("expander", label))


@pytest.fixture(autouse=True)
def preserve_gui_attrs(monkeypatch):
    # Ensure we don't run real streamlit or other helpers from module.
    # Save original attributes to restore later
    originals = {}
    for name in ("get_coder", "get_state", "st"):
        originals[name] = getattr(gui_mod, name, None)
    orig_prompt_as = gui_mod.GUI.prompt_as
    try:
        yield
    finally:
        # restore originals
        for name, val in originals.items():
            if val is None and hasattr(gui_mod, name):
                delattr(gui_mod, name)
            elif val is not None:
                setattr(gui_mod, name, val)
        gui_mod.GUI.prompt_as = orig_prompt_as


def setup_common(monkeypatch, chat_input_return):
    """
    Helper to monkeypatch get_coder, get_state, streamlit functions,
    and GUI methods to safe stubs. Returns (coder, state, message_record, st_calls)
    """
    coder = FakeCoder()
    state = FakeState()
    message_record = []
    messages = FakeMessages(message_record)

    # monkeypatch getters
    monkeypatch.setattr(gui_mod, "get_coder", lambda: coder)
    monkeypatch.setattr(gui_mod, "get_state", lambda: state)

    # Replace GUI methods that would do extra work
    monkeypatch.setattr(gui_mod.GUI, "initialize_state", lambda self: None)
    monkeypatch.setattr(gui_mod.GUI, "do_messages_container", lambda self: setattr(self, "messages", messages))
    monkeypatch.setattr(gui_mod.GUI, "do_sidebar", lambda self: None)
    # Make prompt_pending return False unless test overrides
    monkeypatch.setattr(gui_mod.GUI, "prompt_pending", lambda self: False)
    monkeypatch.setattr(gui_mod.GUI, "process_chat", lambda self: None)

    # Fake streamlit within module
    st_calls = {"chat_input": [], "write": [], "text": [], "rerun": 0}

    class FakeSt:
        def chat_input(self, prompt):
            st_calls["chat_input"].append(prompt)
            return chat_input_return

        def write(self, what):
            st_calls["write"].append(what)

        def text(self, what):
            st_calls["text"].append(what)

        def rerun(self):
            st_calls["rerun"] += 1

    monkeypatch.setattr(gui_mod, "st", FakeSt())

    return coder, state, message_record, st_calls


def test_init_with_user_prompt(monkeypatch):
    # Setup to simulate user entering a chat message
    coder, state, message_record, st_calls = setup_common(monkeypatch, chat_input_return="hello user")

    # Ensure GUI uses 'user' branch
    monkeypatch.setattr(gui_mod.GUI, "prompt_as", "user", raising=False)

    # Instantiate GUI -> should run __init__ and exercise the 'user' branch
    gui = gui_mod.GUI()

    # Assertions about coder flags set by __init__
    assert coder.yield_stream is True
    assert coder.stream is True
    assert coder.pretty is False

    # state.prompt should be set to the chat input
    assert state.prompt == "hello user"
    # coder.io should have recorded the input in history
    assert coder.io.history == ["hello user"]
    # state.input_history appended
    assert state.input_history == ["hello user"]
    # messages appended with the user role
    assert state.messages == [{"role": "user", "content": "hello user"}]

    # The messages context manager for chat_message should have been entered/exited
    # and st.write should have been called with the prompt
    assert any(rec for rec in message_record if rec[1] == ("chat_message", "user"))
    assert st_calls["write"] == ["hello user"]
    # rerun should have been called once at the end
    assert st_calls["rerun"] == 1


def test_init_with_text_prompt(monkeypatch):
    # Setup to simulate user entering a multiline text prompt
    coder, state, message_record, st_calls = setup_common(monkeypatch, chat_input_return="first line\nsecond line")

    # Ensure GUI uses 'text' branch
    monkeypatch.setattr(gui_mod.GUI, "prompt_as", "text", raising=False)

    # Instantiate GUI -> should run __init__ and exercise the 'text' branch
    gui = gui_mod.GUI()

    # coder.io.add_to_input_history should NOT have been called for 'text'
    assert coder.io.history == []

    # state.prompt should be set correctly
    assert state.prompt == "first line\nsecond line"
    # state.input_history appended
    assert state.input_history == ["first line\nsecond line"]
    # messages appended with the text role
    assert state.messages == [{"role": "text", "content": "first line\nsecond line"}]

    # The expander label should be first line + '??'
    expected_label = "first line" + "??"
    # Check that an expander entry with that label was recorded
    assert any(rec for rec in message_record if rec[1] == ("expander", expected_label))

    # st.text should have been called with the full prompt
    assert st_calls["text"] == ["first line\nsecond line"]
    # rerun should have been called once at the end
    assert st_calls["rerun"] == 1
