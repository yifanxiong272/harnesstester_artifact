import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.mdstream')
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
        """Ensure exceptions from live.stop() are suppressed by __del__."""
        ms = MarkdownStream()

        class DummyLive:
            def __init__(self):
                self.stopped = False

            def stop(self):
                self.stopped = True
                raise RuntimeError("stop failed")

        dummy = DummyLive()
        ms.live = dummy

        # Calling the destructor should not raise even though stop() raises.
        try:
            ms.__del__()
        except Exception as e:
            self.fail(f"__del__ propagated an exception: {e}")

        # Verify that stop() was attempted.
        self.assertTrue(dummy.stopped)
