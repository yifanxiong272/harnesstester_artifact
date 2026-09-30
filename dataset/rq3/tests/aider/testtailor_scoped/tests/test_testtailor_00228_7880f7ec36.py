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
        """Test split_chat_history_markdown parses assistant, user and tool blocks and respects include_tool flag."""
        # Try to import the function from a few plausible locations
        split = None
        candidates = [
            "aider.utils.markdown",
            "aider.markdown",
            "aider.utils",
            "aider.chat",
            "aider.main",
        ]
        for modname in candidates:
            try:
                mod = __import__(modname, fromlist=["split_chat_history_markdown"])
                split = getattr(mod, "split_chat_history_markdown", None)
                if split:
                    break
            except Exception:
                continue

        self.assertIsNotNone(split, "Could not import split_chat_history_markdown from expected modules")

        text = (
            "# Title\n"
            "a line from assistant\n"
            "#### /run_tool\n"
            "> output from tool\n"
            "assistant reply line\n"
            "# Another title\n"
        )

        # Default behavior: include_tool=False, tool messages filtered out
        msgs = split(text)
        expected_no_tool = [
            {"role": "assistant", "content": "a line from assistant\n"},
            {"role": "user", "content": "/run_tool\n"},
            {"role": "assistant", "content": "assistant reply line\n"},
        ]
        self.assertEqual(msgs, expected_no_tool)

        # When include_tool=True, tool messages should be present
        msgs_with_tool = split(text, include_tool=True)
        expected_with_tool = [
            {"role": "assistant", "content": "a line from assistant\n"},
            {"role": "user", "content": "/run_tool\n"},
            {"role": "tool", "content": "output from tool\n"},
            {"role": "assistant", "content": "assistant reply line\n"},
        ]
        self.assertEqual(msgs_with_tool, expected_with_tool)
