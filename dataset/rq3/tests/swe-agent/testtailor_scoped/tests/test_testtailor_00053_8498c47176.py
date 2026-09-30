import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.utils')
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
        """Ensure that a multiline command gets its first line augmented with the heredoc marker."""
        action = "mycmd arg\nline1\nline2\nEND\nrest"
        # match_fct should return a re.Match with group(3) = the EOF marker ("END")
        pattern = re.compile(r"(?s)^((mycmd[^\n]*\n(?:.*?\n)*?)(END)\n)")
        def match_fct(s: str):
            return pattern.search(s)
        out = _guard_multiline_input(action, match_fct)
        # The first line of the matched command should have the heredoc appended
        self.assertIn("mycmd arg << 'END'", out)
        # The remainder after the matched block should still be present
        self.assertIn("rest", out)
