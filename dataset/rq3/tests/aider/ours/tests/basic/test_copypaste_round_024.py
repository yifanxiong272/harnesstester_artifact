import importlib
from types import SimpleNamespace

from aider.copypaste import ClipboardWatcher


class FakeEvent:
    def __init__(self, max_false_checks=1):
        # Number of times is_set will return False before returning True
        self._count = 0
        self._max_false = max_false_checks
        self._explicit_set = False

    def is_set(self):
        if self._explicit_set:
            return True
        self._count += 1
        return self._count > self._max_false

    def set(self):
        self._explicit_set = True


class FakeThread:
    def __init__(self, target=None, daemon=False):
        self._target = target
        self.daemon = daemon
        self.started = False
        self.joined = False

    def start(self):
        # Run target synchronously to keep tests deterministic
        self.started = True
        if self._target:
            self._target()

    def join(self):
        self.joined = True


def _make_fake_threading(event_max_false_checks):
    # Return a SimpleNamespace mimicking the threading module used by the module under test
    return SimpleNamespace(Thread=FakeThread, Event=lambda: FakeEvent(max_false_checks=event_max_false_checks))


def test_clipboard_change_round_024(monkeypatch):
    """When clipboard value changes to multi-line, placeholder is wrapped and interrupt called"""
    mod = importlib.import_module("aider.copypaste")

    # Prepare pyperclip.paste to return an initial value then a multi-line changed value
    paste_values = ["initial", "line1\nline2"]

    def fake_paste():
        return paste_values.pop(0)

    monkeypatch.setattr(mod, "pyperclip", SimpleNamespace(paste=fake_paste))

    # Patch time.sleep to no-op to avoid delays
    monkeypatch.setattr(mod, "time", SimpleNamespace(sleep=lambda s: None))

    # Patch threading to use fake threading/event that will allow exactly one loop iteration
    monkeypatch.setattr(mod, "threading", _make_fake_threading(event_max_false_checks=1))

    # Create a simple IO object to observe interactions
    class IO:
        def __init__(self):
            self.clipboard_watcher = None
            self.placeholder = None
            self.interrupt_calls = 0

        def interrupt_input(self):
            self.interrupt_calls += 1

    io = IO()

    cw = ClipboardWatcher(io)
    # start should run the watcher synchronously (FakeThread.start calls target inline)
    cw.start()

    # After one iteration, multi-line placeholder should be wrapped with newlines
    assert io.interrupt_calls == 1, "interrupt_input should have been called once"
    assert io.placeholder == "\n" + "line1\nline2" + "\n"
    assert cw.last_clipboard == "line1\nline2"

    # Stopping should set/clear the watcher references
    cw.stop()
    assert cw.watcher_thread is None and cw.stop_event is None


def test_clipboard_exception_round_024(monkeypatch):
    """When pyperclip.paste raises in watcher, verbose flag triggers dump with message"""
    mod = importlib.import_module("aider.copypaste")

    # Prepare pyperclip.paste to return initial then raise
    state = {"called": 0}

    def fake_paste():
        state["called"] += 1
        if state["called"] == 1:
            return "a"
        raise RuntimeError("boom")

    monkeypatch.setattr(mod, "pyperclip", SimpleNamespace(paste=fake_paste))
    monkeypatch.setattr(mod, "time", SimpleNamespace(sleep=lambda s: None))
    monkeypatch.setattr(mod, "threading", _make_fake_threading(event_max_false_checks=1))

    # Patch aider.dump.dump to capture the dump message
    dump_module = importlib.import_module("aider.dump")
    recorded = []

    def fake_dump(msg):
        recorded.append(msg)

    monkeypatch.setattr(dump_module, "dump", fake_dump)

    class IO:
        def __init__(self):
            self.clipboard_watcher = None
            self.placeholder = None

        def interrupt_input(self):
            # not expected to be called in this flow
            raise AssertionError("interrupt_input should not be called on exception flow")

    io = IO()

    # verbose True to exercise dump() call in exception branch
    cw = ClipboardWatcher(io, verbose=True)
    cw.start()

    # Exception in paste should have been dumped
    assert recorded, "dump should have been called on exception"
    assert any("Clipboard watcher error:" in r and "boom" in r for r in recorded), f"unexpected dump messages: {recorded}"

    # Stop watcher cleanly
    cw.stop()
    assert cw.watcher_thread is None and cw.stop_event is None
