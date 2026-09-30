import types
import pytest

import aider.copypaste as cp
import aider.dump as adump

# Deterministic fake thread that runs the target synchronously
class FakeThread:
    def __init__(self, target, daemon=True):
        self._target = target
        self.daemon = daemon
        self._started = False

    def start(self):
        # Run the target synchronously to keep tests deterministic
        self._started = True
        self._target()

    def join(self, timeout=None):
        # No-op; target already ran synchronously
        return


def make_paste(sequence):
    """Return a paste() callable that yields items from sequence.
    If an item is an Exception instance, calling paste() will raise it.
    After the sequence is exhausted, the last value is returned repeatedly.
    """
    seq = list(sequence)
    index = {"i": 0}

    def paste():
        i = index["i"]
        if i >= len(seq):
            value = seq[-1]
        else:
            value = seq[i]
            index["i"] = i + 1
        if isinstance(value, Exception):
            raise value
        return value

    return paste


class DummyIO:
    def __init__(self):
        self.placeholder = None
        self.interrupted = False
        self.clipboard_watcher = None

    def interrupt_input(self):
        # Mark interrupted and request the watcher to stop deterministically
        self.interrupted = True
        if self.clipboard_watcher and self.clipboard_watcher.stop_event:
            self.clipboard_watcher.stop_event.set()


def _setup_module_patches(paste_callable):
    """Patch the copypaste module to use deterministic thread, sleep, and paste.
    Returns a dict of originals to allow optional restoration.
    """
    originals = {}
    originals['Thread'] = cp.threading.Thread
    originals['sleep'] = cp.time.sleep
    originals['paste'] = cp.pyperclip.paste

    cp.threading.Thread = FakeThread
    cp.time.sleep = lambda _secs: None
    cp.pyperclip.paste = paste_callable

    return originals


def _restore_module_patches(originals):
    cp.threading.Thread = originals['Thread']
    cp.time.sleep = originals['sleep']
    cp.pyperclip.paste = originals['paste']


def test_singleline_change_round_025():
    """Single-line clipboard change should update placeholder without surrounding newlines.

    This covers the loop path where current != last_clipboard and the single-line branch
    (no extra surrounding newlines), and exercises start/stop behavior.
    """
    paste = make_paste(["old", "new"])
    originals = _setup_module_patches(paste)
    try:
        io = DummyIO()
        watcher = cp.ClipboardWatcher(io, verbose=False)
        # __init__ must register the watcher on the io object
        assert io.clipboard_watcher is watcher

        # Start will run synchronously via FakeThread; interrupt_input sets stop_event
        watcher.start()

        # Ensure stop() clears the thread and stop_event attributes
        watcher.stop()

        assert io.placeholder == "new"
        assert watcher.watcher_thread is None and watcher.stop_event is None
        assert io.interrupted is True
    finally:
        _restore_module_patches(originals)


def test_multiline_change_round_025():
    """Multi-line clipboard content should be wrapped with leading and trailing newlines.

    This covers the branch where len(current.splitlines()) > 1 and sets placeholder accordingly.
    """
    multiline = "line1\nline2"
    paste = make_paste(["old", multiline])
    originals = _setup_module_patches(paste)
    try:
        io = DummyIO()
        watcher = cp.ClipboardWatcher(io, verbose=False)
        watcher.start()
        watcher.stop()

        assert io.placeholder == "\n" + multiline + "\n"
        assert io.interrupted is True
    finally:
        _restore_module_patches(originals)


def test_exception_with_verbose_round_025():
    """When pyperclip.paste() raises, and verbose=True, the error is dumped and operation continues.

    This exercises the exception handler branch where aider.dump.dump is called with the error message.
    After the exception, a subsequent successful paste should still trigger an update.
    """
    # Sequence: initial value for last_clipboard, then an exception during the loop,
    # then a final clipboard value to trigger interrupt_input and termination.
    paste_seq = ["a", Exception("boom"), "b"]
    paste = make_paste(paste_seq)

    originals = _setup_module_patches(paste)
    # Patch aider.dump.dump to capture messages
    saved_dump = getattr(adump, 'dump', None)
    dump_messages = []

    def fake_dump(msg):
        dump_messages.append(msg)

    adump.dump = fake_dump

    try:
        io = DummyIO()
        watcher = cp.ClipboardWatcher(io, verbose=True)
        watcher.start()
        watcher.stop()

        # The dump should have been called with a message that contains our exception text
        assert any("Clipboard watcher error" in m and "boom" in m for m in dump_messages)
        # After recovery, placeholder should be updated to the final clipboard value
        assert io.placeholder == "b"
    finally:
        _restore_module_patches(originals)
        # Restore dump to its original reference to avoid side effects
        if saved_dump is None:
            try:
                delattr(adump, 'dump')
            except Exception:
                pass
        else:
            adump.dump = saved_dump
