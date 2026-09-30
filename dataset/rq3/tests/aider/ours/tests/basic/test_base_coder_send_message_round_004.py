import types
import traceback

import pytest

import aider.coders.base_coder as base_coder
from aider.coders.base_coder import Coder, FinishReasonLength


class FakeIO:
    def __init__(self):
        self.llm_started_called = False
        self._assistant_mdstream = object()
        self.tool_warnings = []
        self.tool_errors = []
        self.tool_outputs = []
        self.confirm_answers = []
        self.confirm_asks = []

    def llm_started(self):
        self.llm_started_called = True

    def get_assistant_mdstream(self):
        return self._assistant_mdstream

    def tool_warning(self, msg):
        self.tool_warnings.append(msg)

    def tool_error(self, msg=None):
        self.tool_errors.append(msg)

    def tool_output(self, *args):
        self.tool_outputs.append(args)

    def confirm_ask(self, prompt):
        self.confirm_asks.append(prompt)
        # deterministic default answer (False)
        return False


class FakeWaitingSpinner:
    def __init__(self, msg):
        self.msg = msg
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class _DummyChunks:
    def __init__(self, messages):
        self._messages = messages

    def all_messages(self):
        return list(self._messages)


# Patch out time.sleep and WaitingSpinner and utils.show_messages in module under test
base_coder.time.sleep = lambda *_: None
base_coder.WaitingSpinner = FakeWaitingSpinner


def make_coder():
    # Create a minimal Coder instance without invoking __init__ heavy logic
    coder = Coder.__new__(Coder)
    coder.event_calls = []

    def event(name, **kwargs):
        coder.event_calls.append((name, kwargs))

    coder.event = event
    coder.io = FakeIO()
    coder.cur_messages = []
    coder.functions = None
    coder.multi_response_content = ""
    coder.partial_response_content = None
    coder.partial_response_function_call = False
    coder.reflected_message = None
    coder.num_exhausted_context_windows = 0
    coder.verbose = False
    coder.stream = False
    coder.waiting_spinner = None
    coder.mdstream = None
    coder.main_model = types.SimpleNamespace(name="mm", info={})
    coder._stop_waiting_spinner = lambda: setattr(coder, "_stopped_spinner", True)
    coder.live_incremental_response = lambda final: setattr(coder, "_live_incremental_called", final)
    coder.show_exhausted_error = lambda: setattr(coder, "_show_exhausted_called", True)
    coder.show_pretty = lambda: False
    coder.warm_cache = lambda chunks: setattr(coder, "_warmed", True)
    coder.format_messages = lambda: _DummyChunks(coder.cur_messages)
    coder.get_multi_response_content_in_progress = lambda final=False: "in_progress"
    coder.check_and_open_urls = lambda err, desc: setattr(coder, "_check_open_urls_called", True)
    coder.check_tokens = lambda messages: True
    return coder


def test_check_tokens_false_returns_and_records_llm_start_round_004():
    coder = make_coder()
    # set up state
    coder.cur_messages = []
    coder.io = FakeIO()

    # format_messages -> messages will be one element
    chunks = _DummyChunks([{"role": "user", "content": "hello"}])
    coder.format_messages = lambda: chunks

    # check_tokens returns False to exercise early return (line ~1431-1432)
    coder.check_tokens = lambda messages: False

    # call send_message: it's a generator; converting to list should give [] and not call send
    out = list(Coder.send_message(coder, "hi"))
    assert out == [], "No yielded values expected when check_tokens returns False"
    # llm_started should have been called
    assert coder.io.llm_started_called, "io.llm_started should be called at start"
    # cur_messages should have appended the user message
    assert coder.cur_messages[-1]["role"] == "user" and "hi" in coder.cur_messages[-1]["content"]


def test_verbose_show_messages_and_mdstream_none_round_004(monkeypatch):
    coder = make_coder()
    coder.cur_messages = []
    coder.io = FakeIO()

    # prepare messages so check_tokens returns True
    messages = [{"role": "user", "content": "ask"}]
    chunks = _DummyChunks(messages)
    coder.format_messages = lambda: chunks
    coder.check_tokens = lambda m: True

    # set verbose true to call utils.show_messages
    called = {}

    def fake_show_messages(msgs, functions=None):
        called['args'] = (msgs, functions)

    monkeypatch.setattr(base_coder, "utils", types.SimpleNamespace(show_messages=fake_show_messages))

    coder.verbose = True
    # show_pretty returns False branch -> mdstream should be None
    coder.show_pretty = lambda: False

    # send yields a single value then finishes
    def send_gen(self_messages, functions=None):
        yield "done"

    coder.send = types.MethodType(lambda self, messages, functions=None: send_gen(messages, functions), coder)

    out = list(Coder.send_message(coder, "ask"))
    assert out == ["done"]
    # utils.show_messages called with the messages
    assert 'args' in called and called['args'][0] == messages
    # mdstream should be None in the non-pretty branch
    assert coder.mdstream is None


def test_context_window_exceeded_sets_exhausted_and_appends_assistant_round_004(monkeypatch):
    # Simulate LiteLLMExceptions-driven ContextWindowExceededError handling
    class CustomCtxError(Exception):
        pass

    class FakeLite:
        def exceptions_tuple(self):
            return (CustomCtxError,)

        def get_ex_info(self, err):
            # Return an object with the attributes used in send_message
            return types.SimpleNamespace(name="ContextWindowExceededError", retry=False, description=None)

    monkeypatch.setattr(base_coder, "LiteLLMExceptions", lambda: FakeLite())

    coder = make_coder()
    coder.cur_messages = [{"role": "user", "content": "please"}]
    coder.io = FakeIO()

    # format and token check
    chunks = _DummyChunks(coder.cur_messages)
    coder.format_messages = lambda: chunks
    coder.check_tokens = lambda m: True

    # send will raise the custom context error to be handled
    def send_raiser(messages, functions=None):
        raise CustomCtxError("ctx")
        yield  # pragma: no cover

    coder.send = types.MethodType(lambda self, messages, functions=None: send_raiser(messages, functions), coder)

    # ensure show_pretty False so no spinner complexity
    coder.show_pretty = lambda: False

    # run send_message (generator) to exhaustion
    out = list(Coder.send_message(coder, "go"))
    # out is empty because generator handles internally and returns
    assert out == []
    # exhausted handling should have appended an assistant message
    assert coder.cur_messages[-1]["role"] == "assistant"
    assert "FinishReasonLength" not in (coder.cur_messages[-1].get("content") or "")
    # show_exhausted_error should have been called and counter increased
    assert getattr(coder, "_show_exhausted_called", False) is True
    assert coder.num_exhausted_context_windows == 1
