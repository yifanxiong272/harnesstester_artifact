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
        """Verify that a rapid consecutive non-final update is throttled and returns early."""
        stream = MarkdownStream()

        # First update: should start the Live renderer and set stream.when
        stream.update("Initial content\n\nLine 2\n", final=False)
        initial_when = stream.when

        # Immediate second non-final update should be throttled and return early
        stream.update("Initial content\n\nLine 2\nMore", final=False)

        # If throttled, stream.when should remain unchanged
        self.assertEqual(stream.when, initial_when)

        # Live should have been started
        self.assertTrue(getattr(stream, "_live_started", False))
        self.assertIsNotNone(stream.live)

        # Clean up by issuing a final update which should stop and clear the live instance
        stream.update("Final content\n", final=True)
        self.assertIsNone(stream.live)
