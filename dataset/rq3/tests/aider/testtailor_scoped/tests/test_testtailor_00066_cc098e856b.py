import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.wholefile_coder')
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
        """Ensure a filename longer than 250 chars is cleared and causes a ValueError when no chat files exist."""
        # Create a WholeFileCoder instance without calling its __init__ to avoid external deps.
        coder = object.__new__(WholeFileCoder)

        # Use the standard fence
        coder.fence = ("```", "```")

        # Build content with a filename longer than 250 characters placed immediately before a fence
        longname = "a" * 251
        content = f"{longname}\n{coder.fence[0]}\nprint('hello')\n{coder.fence[1]}\n"

        # Provide the minimal methods/attributes the get_edits path needs.
        coder.get_multi_response_content_in_progress = lambda: content
        coder.get_inchat_relative_files = lambda: []  # no chat files to trigger the ValueError branch

        # Call get_edits and expect a ValueError because the long filename is cleared and no chat files exist.
        with self.assertRaises(ValueError):
            coder.get_edits(mode="update")
