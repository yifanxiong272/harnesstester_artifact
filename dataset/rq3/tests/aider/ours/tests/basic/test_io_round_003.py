import builtins
import types
import pytest

from aider import io as io_mod
from aider.io import InputOutput

# Simple stand-in for ThreadedCompleter to avoid depending on prompt_toolkit internals
class DummyThreadedCompleter:
    def __init__(self, inner):
        self.inner = inner


def _patch_threaded(monkeypatch):
    monkeypatch.setattr(io_mod, "ThreadedCompleter", DummyThreadedCompleter)


def test_get_input_interrupted_returns_file_watcher_command_round_003(monkeypatch):
    """When interrupted and a file_watcher exists, get_input should return process_changes() result,
    start() should have been called before prompting, and stop() called in finally."""
    _patch_threaded(monkeypatch)

    inst = InputOutput()

    # Provide a prompt_session that records the default value passed and returns a line
    class PS:
        def __init__(self):
            self.called = False
            self.default_passed = None

        def prompt(self, *args, **kwargs):
            self.called = True
            self.default_passed = kwargs.get("default")
            return "ignored-line"

    ps = PS()
    inst.prompt_session = ps

    # File watcher that records start/stop/process_changes
    class FW:
        def __init__(self):
            self.started = False
            self.stopped = False
            self.processed = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

        def process_changes(self):
            self.processed = True
            return "RELOAD_CMD"

    fw = FW()
    inst.file_watcher = fw
    inst.clipboard_watcher = None

    # ensure placeholder gets passed through as default
    inst.placeholder = "THE_DEFAULT"

    # Simulate being interrupted before processing result
    inst.interrupted = True

    result = inst.get_input(".", [], [], [])

    assert result == "RELOAD_CMD"
    assert ps.called is True
    assert ps.default_passed == "THE_DEFAULT"
    assert fw.started is True
    assert fw.processed is True
    assert fw.stopped is True


def test_get_input_exception_returns_empty_and_logs_round_003(monkeypatch):
    """If prompt_session.prompt raises a generic Exception, get_input should call tool_error twice and
    return an empty string. Also any watchers should be stopped in the finally block."""
    _patch_threaded(monkeypatch)

    inst = InputOutput()

    class PSBad:
        def prompt(self, *args, **kwargs):
            raise Exception("boom-from-prompt")

    inst.prompt_session = PSBad()

    # watchers to ensure stop() is invoked in finally
    class Watcher:
        def __init__(self):
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    fw = Watcher()
    cw = Watcher()
    inst.file_watcher = fw
    inst.clipboard_watcher = cw

    errors = []

    def capture_tool_error(msg):
        errors.append(msg)

    # Patch instance tool_error so we can assert it was called
    inst.tool_error = capture_tool_error

    result = inst.get_input(".", [], [], [])

    assert result == ""
    # tool_error should be called at least twice (str(err) and traceback)
    assert len(errors) >= 2
    assert fw.stopped is True
    assert cw.stopped is True


def test_get_input_multiline_brace_and_tag_round_003(monkeypatch):
    """Exercise multiline input using a tag. Sequence: user enters '{tag' -> enters lines -> closes with 'tag}'.
    The returned input should contain the accumulated lines with newlines preserved."""
    _patch_threaded(monkeypatch)

    inst = InputOutput()

    # Make prompt_session return a sequence of inputs across prompt calls
    seq = ["{abc", "line one", "abc}"]

    class PSSeq:
        def __init__(self, items):
            self.items = list(items)
            self.calls = 0

        def prompt(self, *args, **kwargs):
            if not self.items:
                return ""
            self.calls += 1
            return self.items.pop(0)

    inst.prompt_session = PSSeq(seq)

    # patch watchers to no-op (they will be started/stopped if code paths do so)
    class NoopWatcher:
        def start(self):
            pass

        def stop(self):
            pass

    inst.file_watcher = NoopWatcher()
    inst.clipboard_watcher = None

    # Capture user_input call
    recorded = {}

    def record_user_input(inp):
        recorded["value"] = inp

    inst.user_input = record_user_input

    result = inst.get_input(".", [], [], [])

    # The multiline content should have the intermediate line with a trailing newline
    assert result == "line one\n"
    # user_input should have been called with the same content
    assert recorded.get("value") == "line one\n"
