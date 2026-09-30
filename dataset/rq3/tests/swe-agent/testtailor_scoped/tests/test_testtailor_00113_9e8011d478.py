import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.common')
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
        """Test AutoCorrectSuggestion.show handles '=' splitting and condition callback."""
        # instance without condition: should detect the --original token after splitting on '='
        s = AutoCorrectSuggestion(original="opt", alternative="alt")
        # when arg contains "=" it should be split and "--opt" should be found
        self.assertTrue(s.show(["--opt=value"]))
        # different option should not match
        self.assertFalse(s.show(["--other=value"]))

        # instance with a condition: ensure the condition receives the split list and return value is used
        seen = []
        def cond(no_equal):
            # capture the received list for assertion and return True only for the expected split
            seen.append(list(no_equal))
            return no_equal == ["--flag", "123"]

        s2 = AutoCorrectSuggestion(original="flag", condition=cond)
        # condition should be called with the split parts and return True for matching case
        self.assertTrue(s2.show(["--flag=123"]))
        self.assertEqual(seen[-1], ["--flag", "123"])

        # non-matching split should cause the condition to return False
        self.assertFalse(s2.show(["--flag", "wrong"]))
        self.assertEqual(seen[-1], ["--flag", "wrong"])
