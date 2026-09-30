import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.core.logger')
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
        """Verify ANSI escape sequences matching the regex are removed and others remain."""
        # Simple single-code sequences
        s1 = "hello\x1B[31mworld\x1B[0m!"
        self.assertEqual(strip_ansi(s1), "helloworld!")

        # Sequence with one semicolon
        s2 = "A\x1B[1;32mB"
        self.assertEqual(strip_ansi(s2), "AB")

        # Sequence with two semicolons (allowed by pattern)
        s3 = "X\x1B[1;2;33mY"
        self.assertEqual(strip_ansi(s3), "XY")

        # Sequence with more than two semicolon groups should NOT be fully matched/removed
        # (pattern only allows up to two (;\d+) groups). Expect the original string to remain.
        s4 = "start\x1B[1;2;3;34mend"
        self.assertEqual(strip_ansi(s4), "start\x1B[1;2;3;34mend")

        # Malformed/incomplete escape (missing trailing 'm') should remain unchanged
        s5 = "incomplete\x1B[31still"
        self.assertEqual(strip_ansi(s5), "incomplete\x1B[31still")

        # Multiple different escape sequences in one string should all be removed when they match
        s6 = "\x1B[0mLead\x1B[1;33mMiddle\x1B[4mTrail"
        # All of these match the pattern (\x1B[<num>(;<num>){0,2}m)
        self.assertEqual(strip_ansi(s6), "LeadMiddleTrail")
