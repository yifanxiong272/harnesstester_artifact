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
        """Destructor should call live.stop and suppress exceptions."""
        stream = MarkdownStream()

        called = {"value": False}

        class BadLive:
            def stop(self_inner):
                called["value"] = True
                raise RuntimeError("stop failed")

        # Attach a live object whose stop() raises an exception
        stream.live = BadLive()

        # Calling the destructor directly should not raise, and stop() should have been invoked
        try:
            stream.__del__()
        except Exception as e:
            self.fail(f"__del__ raised an exception: {e}")

        self.assertTrue(called["value"], "Expected live.stop() to be called in __del__")
