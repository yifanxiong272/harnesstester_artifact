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
        """stop() should call join on watcher_thread, call set on stop_event, and clear both attributes"""
        # lightweight dummy IO object required by ClipboardWatcher
        io = type("IO", (), {})()

        watcher = ClipboardWatcher(io)

        called = {"joined": False, "set": False}

        class DummyThread:
            def join(self):
                called["joined"] = True

        class DummyEvent:
            def set(self):
                called["set"] = True

        # Attach dummy objects so the stop() path that joins the thread is executed
        watcher.watcher_thread = DummyThread()
        watcher.stop_event = DummyEvent()

        # Call stop and verify behavior
        watcher.stop()

        self.assertTrue(called["joined"], "watcher_thread.join() was not called")
        self.assertTrue(called["set"], "stop_event.set() was not called")
        self.assertIsNone(watcher.watcher_thread, "watcher_thread was not cleared")
        self.assertIsNone(watcher.stop_event, "stop_event was not cleared")
