# file: aider/copypaste.py:55-68
# asked: {"lines": [57, 59, 60, 62, 63, 64, 65, 66, 67, 68], "branches": [[64, 65]]}
# gained: {"lines": [57, 59, 60, 62, 63, 64, 65, 66, 67, 68], "branches": [[64, 65]]}

import importlib
import sys
import types

import pytest


def test_main_handles_keyboard_interrupt(monkeypatch, capsys):
    # Create a fake aider.io module with InputOutput class
    fake_io_mod = types.ModuleType("aider.io")

    class FakeInputOutput:
        def __init__(self):
            # mark that an instance was created
            self._created = True

    fake_io_mod.InputOutput = FakeInputOutput

    # Insert fake module into sys.modules so "from aider.io import InputOutput"
    # inside aider.copypaste.main will import our FakeInputOutput.
    monkeypatch.setitem(sys.modules, "aider.io", fake_io_mod)

    # Import the module under test
    import aider.copypaste as copypaste

    # Prepare a FakeClipboardWatcher that records start/stop and the io passed
    events = {}

    class FakeWatcher:
        def __init__(self, io, verbose=False):
            events["io_instance"] = io
            events["verbose"] = verbose
            self.started = False
            self.stopped = False

        def start(self):
            events["start_called"] = True
            self.started = True

        def stop(self):
            events["stop_called"] = True
            self.stopped = True

    # Patch the ClipboardWatcher used in aider.copypaste
    monkeypatch.setattr(copypaste, "ClipboardWatcher", FakeWatcher, raising=False)

    # Patch the time.sleep used in aider.copypaste to raise KeyboardInterrupt immediately,
    # which should trigger the except block and call watcher.stop()
    def raise_keyboard_interrupt(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(copypaste.time, "sleep", raise_keyboard_interrupt)

    # Run main -- it should catch the KeyboardInterrupt, print the message, and call stop.
    copypaste.main()

    # Assertions to verify postconditions and that the except branch was executed
    assert events.get("start_called") is True, "watcher.start() was not called"
    assert events.get("stop_called") is True, "watcher.stop() was not called"
    assert isinstance(events.get("io_instance"), FakeInputOutput)
    assert events.get("verbose") is True

    captured = capsys.readouterr()
    assert "Stopped watching clipboard" in captured.out
