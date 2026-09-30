import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.utils')
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
        """Verify split_chat_history_markdown parses assistant/user/tool messages and respects include_tool."""
        text = (
            "# Title\n"
            "> tool output line1\n"
            "#### /toolname\n"
            "User question\n"
            "> assistant reply\n"
            "Final assistant answer\n"
        )

        # When tools are excluded
        msgs_no_tool = split_chat_history_markdown(text, include_tool=False)
        expected_no_tool = [
            {"role": "user", "content": "/toolname\n"},
            {"role": "assistant", "content": "User question\n"},
            {"role": "assistant", "content": "Final assistant answer\n"},
        ]
        self.assertEqual(msgs_no_tool, expected_no_tool)

        # When tools are included
        msgs_with_tool = split_chat_history_markdown(text, include_tool=True)
        expected_with_tool = [
            {"role": "tool", "content": "tool output line1\n"},
            {"role": "user", "content": "/toolname\n"},
            {"role": "assistant", "content": "User question\n"},
            {"role": "tool", "content": "assistant reply\n"},
            {"role": "assistant", "content": "Final assistant answer\n"},
        ]
        self.assertEqual(msgs_with_tool, expected_with_tool)
