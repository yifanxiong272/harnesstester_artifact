import types
import pytest

import aider.gui as gui


class FakeIO:
    def __init__(self):
        self.added = []

    def add_to_input_history(self, val):
        self.added.append(val)


class FakeCoder:
    def __init__(self):
        self.io = FakeIO()
        # these attributes are set by GUI.__init__ in real code
        self.yield_stream = False
        self.stream = False
        self.pretty = True


class FakeState:
    def __init__(self):
        self.prompt = None
        self.input_history = []
        self.messages = []


class Ctx:
    def __init__(self, rec, kind):
        self.rec = rec
        self.kind = kind

    def __enter__(self):
        # record that the context was entered with its kind
        self.rec.append(("enter", self.kind))
        return self

    def __exit__(self, exc_type, exc, tb):
        self.rec.append(("exit", self.kind))
        return False


class FakeMessages:
    def __init__(self):
        self.rec = []

    def chat_message(self, who):
        return Ctx(self.rec, ("chat_message", who))

    def expander(self, name):
        return Ctx(self.rec, ("expander", name))


class FakeSt:
    def __init__(self, chat_input_value):
        self._chat_input_value = chat_input_value
        self.written = []
        self.texted = []
        self.rerun_count = 0

    def chat_input(self, prompt):
        # always deterministic
        return self._chat_input_value

    def write(self, val):
        self.written.append(val)

    def text(self, val):
        self.texted.append(val)

    def rerun(self):
        self.rerun_count += 1


# Helper to construct and patch GUI environment deterministically
def _make_env(monkeypatch, chat_input_value, prompt_as, prompt_pending=False):
    coder = FakeCoder()
    state = FakeState()
    fake_messages = FakeMessages()
    fake_st = FakeSt(chat_input_value)

    # patch functions and module-level st in aider.gui
    monkeypatch.setattr(gui, "get_coder", lambda: coder)
    monkeypatch.setattr(gui, "get_state", lambda: state)
    monkeypatch.setattr(gui, "st", fake_st)

    # patch GUI.setup-like methods; initialize_state is called inside __init__ and should set prompt_as & messages
    def initialize_state(self):
        # set the attribute used later
        self.prompt_as = prompt_as
        # attach the fake messages object so with self.messages.chat_message/expander works
        self.messages = fake_messages
        # also ensure self.state is the patched state (GUI.__init__ sets self.state = get_state())
    monkeypatch.setattr(gui.GUI, "initialize_state", initialize_state)

    # prevent side effects from rendering helpers
    monkeypatch.setattr(gui.GUI, "do_messages_container", lambda self: None)
    monkeypatch.setattr(gui.GUI, "do_sidebar", lambda self: None)

    # control prompt_pending behavior
    monkeypatch.setattr(gui.GUI, "prompt_pending", lambda self: prompt_pending)

    return coder, state, fake_messages, fake_st


def test_no_input_returns_round_023(monkeypatch):
    # Case: no user input -> early return at "if not self.prompt: return"
    coder, state, fake_messages, fake_st = _make_env(monkeypatch, chat_input_value="", prompt_as=None, prompt_pending=False)

    # instantiate GUI; __init__ runs the path with empty chat_input
    gui.GUI()

    # Because prompt was empty, __init__ should return early and not call rerun()
    assert fake_st.rerun_count == 0

    # state.prompt should remain None (initialize_state did not set it)
    assert state.prompt is None

    # no additions to input history
    assert coder.io.added == []
    # no messages appended
    assert state.messages == []


def test_user_prompt_with_pending_round_023(monkeypatch):
    # Case: user provides input, prompt_pending True so process_chat() is invoked
    # and then the rest of the path runs for prompt_as == "user"
    coder, state, fake_messages, fake_st = _make_env(monkeypatch, chat_input_value="hello user", prompt_as="user", prompt_pending=True)

    called = {}

    def fake_process_chat(self):
        called['process_chat'] = True
        # do not modify prompt; allow continuation of __init__ after this

    monkeypatch.setattr(gui.GUI, "process_chat", fake_process_chat)

    g = gui.GUI()

    # process_chat must have been invoked
    assert called.get('process_chat', False) is True

    # after __init__, state.prompt should equal provided prompt
    assert state.prompt == "hello user"

    # coder IO history must have the prompt (prompt_as == "user")
    assert coder.io.added == ["hello user"]

    # input_history appended
    assert state.input_history == ["hello user"]

    # messages list appended with dict containing role and content
    assert state.messages == [{"role": "user", "content": "hello user"}]

    # the messages.chat_message context manager should have been entered with "user"
    # (it records enter/exit tuples in fake_messages.rec)
    assert ("enter", ("chat_message", "user")) in g.messages.rec
    assert ("exit", ("chat_message", "user")) in g.messages.rec

    # st.write called with the prompt
    assert fake_st.written == ["hello user"]

    # st.rerun should be called once at the end
    assert fake_st.rerun_count == 1


def test_text_prompt_round_023(monkeypatch):
    # Case: prompt_as == "text" should take the expander branch
    prompt_value = "first line\nsecond line"
    coder, state, fake_messages, fake_st = _make_env(monkeypatch, chat_input_value=prompt_value, prompt_as="text", prompt_pending=False)

    g = gui.GUI()

    # state.prompt should be set to prompt_value
    assert state.prompt == prompt_value

    # coder IO should not have been called for text prompts
    assert coder.io.added == []

    # input_history appended
    assert state.input_history == [prompt_value]

    # messages list appended with the text role
    assert state.messages == [{"role": "text", "content": prompt_value}]

    # The expander name should be the first line + '??'
    expected_expander_name = prompt_value.splitlines()[0] + "??"
    # The expander context manager is recorded with its name in fake_messages.rec
    # It stores tuples like ("enter", ("expander", name))
    assert ("enter", ("expander", expected_expander_name)) in g.messages.rec
    assert ("exit", ("expander", expected_expander_name)) in g.messages.rec

    # st.text should be called with the full prompt inside the expander
    assert fake_st.texted == [prompt_value]

    # st.rerun should be called once
    assert fake_st.rerun_count == 1
