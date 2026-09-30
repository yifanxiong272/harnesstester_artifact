# file: aider/copypaste.py:7-52
# asked: {"lines": [11, 12, 13, 14, 15, 16, 20, 21, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 39, 40, 42, 43, 47, 48, 49, 50, 51, 52], "branches": [[24, 0], [24, 25], [27, 28], [27, 34], [31, 32], [31, 34], [36, 37], [36, 40], [47, 48], [47, 49], [49, 0], [49, 50]]}
# gained: {"lines": [11, 12, 13, 14, 15, 16, 20, 21, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 39, 40, 42, 43, 47, 48, 49, 50, 51, 52], "branches": [[24, 0], [24, 25], [27, 28], [27, 34], [31, 32], [31, 34], [36, 37], [36, 40], [47, 48], [49, 50]]}

import sys
import types
import time as real_time
import threading

import pytest

from aider.copypaste import ClipboardWatcher

class DummyIO:
    def __init__(self):
        self.placeholder = None
        self.interrupted = 0
        self.clipboard_watcher = None

    def interrupt_input(self):
        self.interrupted += 1


def _fast_sleep(s):
    # keep behavior but very fast to avoid long running tests
    real_time.sleep(min(0.001, s))


def test_single_line_clipboard_change(monkeypatch):
    """
    Verify that when clipboard content changes to a single-line string,
    the IO placeholder is updated to that string and interrupt_input is called.
    """
    io = DummyIO()
    watcher = None

    # prepare side effect for pyperclip.paste:
    # first call (start) -> 'initial'
    # second call (in watcher loop) -> 'new' and set stop_event to stop the watcher
    calls = {"count": 0}
    def paste_side_effect():
        calls["count"] += 1
        if calls["count"] == 1:
            return "initial"
        elif calls["count"] == 2:
            # stop the watcher after the change is observed to let the thread exit
            if watcher is not None and watcher.stop_event is not None:
                watcher.stop_event.set()
            return "new"
        else:
            return "new"

    monkeypatch.setattr('aider.copypaste.pyperclip.paste', lambda: paste_side_effect())
    monkeypatch.setattr('aider.copypaste.time.sleep', _fast_sleep)

    watcher = ClipboardWatcher(io, verbose=False)
    watcher.start()

    # Wait for thread to finish (stop_event is set inside paste_side_effect)
    watcher.stop()

    assert io.interrupted >= 1, "interrupt_input should have been called at least once"
    assert io.placeholder == "new", "Placeholder should be updated to the new single-line clipboard content"
    # ensure cleanup
    assert watcher.watcher_thread is None
    assert watcher.stop_event is None


def test_multi_line_clipboard_change_wraps_placeholder(monkeypatch):
    """
    Verify that when clipboard content changes to multi-line string,
    the IO placeholder is wrapped with surrounding newlines.
    """
    io = DummyIO()
    watcher = None

    calls = {"count": 0}
    multi = "line1\nline2"
    def paste_side_effect():
        calls["count"] += 1
        if calls["count"] == 1:
            return "initial"
        elif calls["count"] == 2:
            # ask watcher to stop after observing the change
            if watcher is not None and watcher.stop_event is not None:
                watcher.stop_event.set()
            return multi
        else:
            return multi

    monkeypatch.setattr('aider.copypaste.pyperclip.paste', lambda: paste_side_effect())
    monkeypatch.setattr('aider.copypaste.time.sleep', _fast_sleep)

    watcher = ClipboardWatcher(io, verbose=False)
    watcher.start()
    watcher.stop()

    assert io.interrupted >= 1
    assert io.placeholder == "\n" + multi + "\n", "Multi-line placeholder must be wrapped with newlines"
    assert watcher.watcher_thread is None
    assert watcher.stop_event is None


def test_exception_in_paste_calls_dump_when_verbose(monkeypatch):
    """
    Force pyperclip.paste to raise inside the watcher loop and verify that
    when verbose=True the aider.dump.dump function is called with the error message.
    """
    io = DummyIO()
    watcher = None

    # Install a fake aider.dump module to capture the dump() call
    dump_calls = []
    mod = types.ModuleType("aider.dump")
    def fake_dump(msg):
        dump_calls.append(msg)
    mod.dump = fake_dump
    sys.modules['aider.dump'] = mod

    calls = {"count": 0}
    def paste_side_effect():
        calls["count"] += 1
        if calls["count"] == 1:
            return "initial"
        elif calls["count"] == 2:
            # simulate an error during paste inside the thread loop
            raise RuntimeError("boom")
        else:
            # after the error, stop the watcher so the loop will exit
            if watcher is not None and watcher.stop_event is not None:
                watcher.stop_event.set()
            return "initial"

    monkeypatch.setattr('aider.copypaste.pyperclip.paste', lambda: paste_side_effect())
    monkeypatch.setattr('aider.copypaste.time.sleep', _fast_sleep)

    watcher = ClipboardWatcher(io, verbose=True)
    watcher.start()
    watcher.stop()

    # check that dump was called and contains the exception message
    assert any("Clipboard watcher error" in m and "boom" in m for m in dump_calls), (
        "dump should be called with the clipboard watcher error message when verbose=True"
    )

    # cleanup injected module
    del sys.modules['aider.dump']
    assert watcher.watcher_thread is None
    assert watcher.stop_event is None
