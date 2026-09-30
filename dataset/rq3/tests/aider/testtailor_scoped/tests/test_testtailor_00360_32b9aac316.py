import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.coders.patch_coder')
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
        """Verify peek_next_section parses a simple update section with one chunk."""
        lines = [
            " context line 1",
            "-deleted line",
            "+added line",
            " context line 2",
            "@@ some other",  # section terminator
        ]

        context_lines, chunks, next_index, is_eof = peek_next_section(lines, 0)

        # Basic checks
        self.assertFalse(is_eof)
        self.assertEqual(next_index, 4)  # stopped at the terminator line

        # Context lines should include the kept and deleted lines (without prefixes)
        self.assertEqual(
            context_lines, ["context line 1", "deleted line", "context line 2"]
        )

        # One chunk should have been created for the delete+add pair
        self.assertEqual(len(chunks), 1)
        chunk = chunks[0]
        self.assertEqual(chunk.orig_index, 1)  # start index in the original context
        self.assertEqual(chunk.del_lines, ["deleted line"])
        self.assertEqual(chunk.ins_lines, ["added line"])
