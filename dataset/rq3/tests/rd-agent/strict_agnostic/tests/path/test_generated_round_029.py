import importlib
from types import SimpleNamespace
import rdagent.log.ui.web as web


class DummyWindow:
    def __init__(self, *args, **kwargs):
        self.last_msg = None

    def consume_msg(self, msg):
        # record that consume_msg was called with this msg
        self.last_msg = msg


class DummyLLMWindow(DummyWindow):
    pass


class DummyContainer:
    def __init__(self):
        self.header_calls = []
        self.expanders = {}

    def header(self, text, divider=False):
        # record header calls for assertions
        self.header_calls.append((text, divider))

    def expander(self, name):
        # return a simple placeholder object used by windows if needed
        obj = SimpleNamespace(name=name)
        self.expanders[name] = obj
        return obj


def _monkeypatch_windows():
    """Replace certain window classes in the module with lightweight dummies
    so tests are deterministic and do not depend on heavy UI behavior.
    """
    web.StWindow = DummyWindow
    web.LLMWindow = DummyLLMWindow
    # Other windows are left as-is because tests avoid exercising those branches.


def test_header_and_common_logs_round_029():
    # Arrange: monkeypatch Windows to lean dummies and prepare container
    _monkeypatch_windows()
    container = DummyContainer()

    # Create the SimpleTraceWindow under test
    stw = web.SimpleTraceWindow(container, show_llm=True, show_common_logs=True)

    # Make sure current_tag starts as empty so header branch triggers
    assert getattr(stw, "current_tag", "") == "" or isinstance(stw.current_tag, str)

    # Create a message whose tag is longer than current_tag and does not end with llm_messages
    msg = SimpleNamespace(tag="task.one", content="a plain text log")

    # Act
    stw.consume_msg(msg)

    # Assert: header was called with dotted tag turned into arrow-separated text
    # The code uses the unicode arrow \u27a1 between segments
    expected_header_text = msg.tag.replace(".", " \u27a1 ")
    assert container.header_calls, "header should have been called"
    assert container.header_calls[-1] == (expected_header_text, True)

    # Assert: after processing common logs, the current window is our DummyWindow and it consumed the message
    assert isinstance(stw.current_win, DummyWindow)
    assert stw.current_win.last_msg is msg


def test_llm_messages_hide_and_show_round_029():
    # Arrange
    _monkeypatch_windows()
    container = DummyContainer()

    # Case A: show_llm is False -> llm message should early-return and not change current_win
    stw_hide = web.SimpleTraceWindow(container, show_llm=False, show_common_logs=True)
    orig_win = DummyWindow()
    stw_hide.current_win = orig_win

    msg_llm = SimpleNamespace(tag="session.llm_messages", content="irrelevant")

    # Act
    stw_hide.consume_msg(msg_llm)

    # Assert: current_win unchanged and no consume_msg called on the original window
    assert stw_hide.current_win is orig_win
    assert orig_win.last_msg is None

    # Case B: show_llm is True -> should create an LLMWindow (DummyLLMWindow) and call its consume_msg
    stw_show = web.SimpleTraceWindow(container, show_llm=True, show_common_logs=True)
    # ensure current_win is not already an LLMWindow to force creation
    stw_show.current_win = DummyWindow()

    msg_llm2 = SimpleNamespace(tag="session.llm_messages", content="llm text")

    # Act
    stw_show.consume_msg(msg_llm2)

    # Assert: current_win replaced by DummyLLMWindow and it consumed the message
    assert isinstance(stw_show.current_win, DummyLLMWindow)
    assert stw_show.current_win.last_msg is msg_llm2


def test_list_empty_return_round_029():
    # Arrange: ensure simple dummy windows for deterministic behavior
    _monkeypatch_windows()
    container = DummyContainer()

    stw = web.SimpleTraceWindow(container, show_llm=True, show_common_logs=True)
    orig_win = DummyWindow()
    stw.current_win = orig_win

    # Provide an explicit empty list as content; the code filters falsy elements then returns early
    msg_list_empty = SimpleNamespace(tag="some.tag", content=[])

    # Act
    stw.consume_msg(msg_list_empty)

    # Assert: because list becomes empty, the method should return early and not call consume_msg on current window
    assert stw.current_win is orig_win
    assert orig_win.last_msg is None

    # Also test that a list of falsy elements likewise becomes empty after filtering
    stw2 = web.SimpleTraceWindow(container, show_llm=True, show_common_logs=True)
    stw2.current_win = DummyWindow()
    msg_list_falsy = SimpleNamespace(tag="other.tag", content=[None, "", 0])

    stw2.consume_msg(msg_list_falsy)

    # After filtering the list, it should be empty and the current window should not have consumed the message
    assert stw2.current_win.last_msg is None
