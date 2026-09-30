import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.context_coder')
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
        """Ensure reply_completed returns True when mentioned files match current in-chat files."""
        # Create instance without running __init__
        inst = ContextCoder.__new__(ContextCoder)

        # Non-empty content so early empty checks pass
        inst.partial_response_content = "Please edit a.py and b.py"

        # Provide methods that return identical sets so mentioned_rel_fnames == current_rel_fnames
        def fake_get_inchat_relative_files():
            return ["a.py", "b.py"]

        def fake_get_file_mentions(content, ignore_current=True):
            # ensure the function signature matches the call in reply_completed
            return ["a.py", "b.py"]

        inst.get_inchat_relative_files = fake_get_inchat_relative_files
        inst.get_file_mentions = fake_get_file_mentions

        # Call the method under test and assert it returns True (takes the equality branch)
        result = inst.reply_completed()
        self.assertTrue(result)
