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
        """Verify that falsy mdargs results in a new empty dict being used."""
        # Pass an empty dict (falsy) and ensure the instance creates a new dict
        original = {}
        stream = MarkdownStream(mdargs=original)

        # mdargs should be a dict, empty, and not the same object as the one passed in
        self.assertIsInstance(stream.mdargs, dict)
        self.assertEqual(stream.mdargs, {})
        self.assertIsNot(stream.mdargs, original)

        # Also verify defaults set in __init__
        self.assertEqual(stream.printed, [])
        self.assertIsNone(stream.live)
        self.assertFalse(getattr(stream, "_live_started", True))

        # And verify behavior when mdargs is omitted entirely
        stream2 = MarkdownStream()
        self.assertIsInstance(stream2.mdargs, dict)
        self.assertEqual(stream2.mdargs, {})
        self.assertIsNone(stream2.live)
        self.assertFalse(getattr(stream2, "_live_started", True))
