import pytest

import types

import aider.gui as gui


class FakeIO:
    def __init__(self):
        self.added = []

    def add_to_input_history(self, v):
        self.added.append(v)


class FakeCoder:
    def __init__(self):
        self.io = FakeIO()
        self.yield_stream = False
        self.stream = False
        self.pretty = True


class FakeState:
    def __init__(self):
        self.prompt = None
        self.input_history = []
        self.messages = []


class _Ctx:
    def __init__(self, record_list, label):
        self.record_list = record_list
        self.label = label

    def __enter__(self):
        # return something harmless
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeMessages:
    def __init__(self):
        self.chat_message_called = []
        self.expander_called = []

    def chat_message(self, role):
        # record and return context manager
        self.chat_message_called.append(role)
        return _Ctx(self.chat_message_called, role)

    def expander(self, label):
        self.expander_called.append(label)
        return _Ctx(self.expander_called, label)


class FakeSt:
    def __init__(self, chat_input_value):
        self._chat_input_value = chat_input_value
        self.write_called = []
        self.text_called = []
        self.rerun_called = False

    def chat_input(self, prompt):
        # deterministic fake user input
        return self._chat_input_value

    def write(self, v):
        self.write_called.append(v)

    def text(self, v):
        self.text_called.append(v)

    def rerun(self):
        # don't actually exit or re-run test environment; just record call
        self.rerun_called = True


def _patch_common(monkeypatch, chat_input_value, prompt_as, prompt_pending=False):
    """Helper to patch module-level dependencies for GUI.__init__."""
    fake_coder = FakeCoder()
    fake_state = FakeState()
    fake_messages = FakeMessages()
    fake_st = FakeSt(chat_input_value)

    # patch the module-level dependences
    monkeypatch.setattr(gui, "get_coder", lambda: fake_coder)
    monkeypatch.setattr(gui, "get_state", lambda: fake_state)

    # Replace the streamlit module used by the GUI module
    monkeypatch.setattr(gui, "st", fake_st)

    # Prevent heavy UI logic in these methods inside __init__
    monkeypatch.setattr(gui.GUI, "do_messages_container", lambda self: None, raising=False)
    monkeypatch.setattr(gui.GUI, "do_sidebar", lambda self: None, raising=False)

    # initialize_state is called inside __init__; set it to prepare the instance
    def _fake_initialize_state(self):
        # set prompt_as for branch selection and set messages interface
        self.prompt_as = prompt_as
        # GUI.__init__ will set self.state = get_state() before calling this
        # attach a messages object used later in __init__
        self.messages = fake_messages

    monkeypatch.setattr(gui.GUI, "initialize_state", _fake_initialize_state, raising=False)

    # Control prompt_pending behavior
    monkeypatch.setattr(gui.GUI, "prompt_pending", (lambda self: prompt_pending), raising=False)

    return fake_coder, fake_state, fake_messages, fake_st


def test_init_no_input_round_024(monkeypatch):
    """When chat_input returns falsy and no prompt is pending, __init__ should return early and not call rerun."""
    fake_coder, fake_state, fake_messages, fake_st = _patch_common(
        monkeypatch, chat_input_value="", prompt_as=None, prompt_pending=False
    )

    # Instantiate the GUI; __init__ should return early due to no prompt
    g = gui.GUI()

    # Because there was no prompt, coder IO should not have been touched
    assert fake_coder.io.added == []

    # State input history should remain empty
    assert fake_state.input_history == []

    # No messages should have been appended to state.messages
    assert fake_state.messages == []

    # Because __init__ returned early, st.rerun should not have been called
    assert fake_st.rerun_called is False


def test_init_with_user_prompt_round_024(monkeypatch):
    """When chat_input returns a user prompt and prompt_as == 'user', the prompt should be recorded to coder IO, state, messages and st.write should be used."""
    fake_coder, fake_state, fake_messages, fake_st = _patch_common(
        monkeypatch, chat_input_value="hello user", prompt_as="user", prompt_pending=False
    )

    # Instantiate GUI which will exercise the 'user' branch
    g = gui.GUI()

    # The coder IO should have recorded the prompt
    assert fake_coder.io.added == ["hello user"]

    # State input history should include the prompt
    assert fake_state.input_history == ["hello user"]

    # State messages should get the appended dict for the role 'user'
    # the code appends to self.state.messages at line 392 when prompt_as is truthy
    assert any(m.get("role") == "user" and m.get("content") == "hello user" for m in fake_state.messages)

    # The chat_message context manager branch for 'user' should have been entered
    assert fake_messages.chat_message_called and fake_messages.chat_message_called[-1] == "user"

    # st.write should have been called with the prompt inside the chat message
    assert fake_st.write_called == ["hello user"]

    # At the end of __init__, st.rerun should be invoked to re-render
    assert fake_st.rerun_called is True


def test_init_with_text_prompt_round_024(monkeypatch):
    """When chat_input returns multi-line text and prompt_as == 'text', the expander label should be first line + '??' and st.text called with full prompt."""
    prompt_text = "line1\nline2"
    fake_coder, fake_state, fake_messages, fake_st = _patch_common(
        monkeypatch, chat_input_value=prompt_text, prompt_as="text", prompt_pending=False
    )

    # Instantiate GUI which will exercise the 'text' branch
    g = gui.GUI()

    # State input history should include the prompt
    assert fake_state.input_history == [prompt_text]

    # A message entry should have been appended with role 'text'
    assert any(m.get("role") == "text" and m.get("content") == prompt_text for m in fake_state.messages)

    # Expander should have been called with the first line + '??'
    assert fake_messages.expander_called
    assert fake_messages.expander_called[-1] == "line1??"

    # st.text should have been called with the full prompt inside the expander
    assert fake_st.text_called == [prompt_text]

    # st.rerun should have been called to trigger UI re-render
    assert fake_st.rerun_called is True
