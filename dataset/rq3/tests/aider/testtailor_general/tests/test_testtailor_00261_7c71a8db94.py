import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.copypaste')
except Exception:
    _testtailor_target = None
else:
    globals().update({
        name: value
        for name, value in vars(_testtailor_target).items()
        if not name.startswith("__")
    })

class _TestTailorTimeout:
    @staticmethod
    def timeout(_seconds):
        return lambda function: function

timeout_decorator = _TestTailorTimeout()

class Test(unittest.TestCase):
    @timeout_decorator.timeout(1)
    def test_case_XX(self):
        """stop() should set stop_event when it's present"""
        class DummyIO:
            pass

        io = DummyIO()
        watcher = ClipboardWatcher(io)
        # initially no stop_event
        self.assertIsNone(watcher.stop_event)
        self.assertIsNone(watcher.watcher_thread)

        # provide a stop_event and call stop()
        ev = threading.Event()
        watcher.stop_event = ev
        watcher.stop()

        # stop_event.set() should have been called
        self.assertTrue(ev.is_set())
        # watcher_thread should remain None and stop_event should still reference the event
        self.assertIsNone(watcher.watcher_thread)
        self.assertIs(watcher.stop_event, ev)
