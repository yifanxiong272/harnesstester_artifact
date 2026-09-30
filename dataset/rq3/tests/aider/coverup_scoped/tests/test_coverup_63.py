# file: aider/coders/base_coder.py:924-944
# asked: {"lines": [930, 939, 940, 941, 943, 944], "branches": [[927, 930], [932, 0], [936, 939], [939, 940], [939, 943]]}
# gained: {"lines": [930, 939, 940, 941, 943, 944], "branches": [[927, 930], [936, 939], [939, 940], [939, 943]]}

import pytest
from types import SimpleNamespace

try:
    from aider.coders.base_coder import Coder
except Exception as e:
    pytest.skip(f"Couldn't import Coder: {e}", allow_module_level=True)


class DummyModel:
    def __init__(self):
        # ChatSummary expects weak_model.token_count to exist
        self.weak_model = SimpleNamespace(token_count=0)
        self.reasoning_tag = None
        self.streaming = True
        self.info = {"max_input_tokens": 0}
        self.max_chat_history_tokens = 1024

    def commit_message_models(self):
        return []


class DummyIO:
    def __init__(self):
        self.pretty = False
        self.encoding = "utf-8"
        self.chat_history_file = "nonexistent_history.md"
        self._warnings = []
        self._outputs = []

    def read_text(self, path):
        return ""

    def tool_warning(self, msg):
        self._warnings.append(msg)

    def tool_output(self, msg):
        self._outputs.append(msg)


def make_coder():
    main_model = DummyModel()
    io = DummyIO()
    coder = Coder(main_model, io, repo=None, fnames=[])
    return coder


def test_run_one_triggers_tool_warning(monkeypatch):
    coder = make_coder()

    # Provide required minimal methods/attributes for run_one
    monkeypatch.setattr(coder, "init_before_message", lambda: None)
    monkeypatch.setattr(coder, "preproc_user_input", lambda x: "PRE:" + x)

    # Set reflections so that the warning path is taken immediately (num_reflections >= max_reflections)
    coder.num_reflections = 0
    coder.max_reflections = 0

    # send_message must set reflected_message to a non-empty value to reach the max_reflections check
    def send_message(message):
        coder.reflected_message = "will_trigger_warning"
        yield "ok"

    monkeypatch.setattr(coder, "send_message", send_message)

    # Call with preproc=False to exercise the branch where message = user_message
    result = coder.run_one("original_input", preproc=False)

    # After run_one returns (due to warning), the warning must have been recorded and no reflections incremented
    assert coder.io._warnings == ["Only 0 reflections allowed, stopping."]
    assert coder.num_reflections == 0
    assert result is None


def test_run_one_increments_reflections_and_terminates(monkeypatch):
    coder = make_coder()

    # Minimal required methods
    monkeypatch.setattr(coder, "init_before_message", lambda: None)
    monkeypatch.setattr(coder, "preproc_user_input", lambda x: "PRE:" + x)

    # Allow at least one reflection (so we take the increment branch)
    coder.num_reflections = 0
    coder.max_reflections = 5

    # Track number of times send_message is invoked
    call_state = {"calls": 0}

    def send_message(message):
        # First call: set a reflected message to continue the loop.
        # Second call: set reflected_message to None so the loop breaks.
        if call_state["calls"] == 0:
            coder.reflected_message = "next_message"
        else:
            coder.reflected_message = None
        call_state["calls"] += 1
        yield "ok"

    monkeypatch.setattr(coder, "send_message", send_message)

    # Ensure tool_warning is not called in this test
    def tool_warning_should_not_be_called(msg):
        raise AssertionError("tool_warning should not be called in this test")

    coder.io.tool_warning = tool_warning_should_not_be_called

    # Call with preproc=False to hit the message = user_message branch
    coder.run_one("start_input", preproc=False)

    # After two iterations: num_reflections should have incremented once,
    # send_message should have been called twice (once per loop iteration).
    assert coder.num_reflections == 1
    assert call_state["calls"] == 2
    # After termination, reflected_message should be None (because second iteration set it to None)
    assert coder.reflected_message is None
