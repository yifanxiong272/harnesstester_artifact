import sys
import types
import importlib

import pytest


def test_main_keyboardinterrupt_round_170(monkeypatch, capsys):
    """Exercise main() so it enters the try/except and calls watcher.stop().

    Strategy:
    - Provide a fake aider.io module with an InputOutput constructor so the
      runtime import inside main() finds it.
    - Patch aider.copypaste.ClipboardWatcher with a FakeWatcher that records
      the instance created so the test can assert start()/stop() were called.
    - Patch aider.copypaste.time.sleep to raise KeyboardInterrupt on first
      call so the infinite loop in main() breaks deterministically.
    - Capture stdout to assert the expected message is printed.
    """

    # Create and inject a fake aider.io module with an InputOutput class
    fake_io_mod = types.ModuleType("aider.io")

    class DummyInputOutput:
        def __init__(self):
            # Marker to allow assertions that an instance was created
            self._dummy_io_created = True

    fake_io_mod.InputOutput = DummyInputOutput
    monkeypatch.setitem(sys.modules, 'aider.io', fake_io_mod)

    # Import the module under test (or get existing import)
    import aider.copypaste as copypaste
    importlib.reload(copypaste)

    # Define a FakeWatcher that records the instance and start/stop calls
    class FakeWatcher:
        last_instance = None

        def __init__(self, io, verbose=True):
            # record the instance for later assertions
            FakeWatcher.last_instance = self
            self.io = io
            self.verbose = verbose
            self.started = False
            self.stopped = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

    # Patch the ClipboardWatcher used inside main
    monkeypatch.setattr(copypaste, 'ClipboardWatcher', FakeWatcher)

    # Patch time.sleep in the module so the infinite loop raises KeyboardInterrupt
    def raising_sleep(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(copypaste.time, 'sleep', raising_sleep)

    # Run the function under test; it should handle the KeyboardInterrupt,
    # print the stop message, and call watcher.stop()
    copypaste.main()

    # Capture stdout and assert printed message
    captured = capsys.readouterr()
    assert "Stopped watching clipboard" in captured.out

    # Assert the FakeWatcher instance was created and its methods were invoked
    inst = FakeWatcher.last_instance
    assert inst is not None, "ClipboardWatcher was not instantiated"
    assert isinstance(inst.io, DummyInputOutput), "InputOutput instance was not passed to ClipboardWatcher"
    assert inst.started is True, "ClipboardWatcher.start() was not called"
    assert inst.stopped is True, "ClipboardWatcher.stop() was not called"
