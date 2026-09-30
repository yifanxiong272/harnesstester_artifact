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
        """Ensure code path where a match is found after some pre-action (pre_action != '') is exercised.
        The matcher returns a match with three capture groups so that first_match.group(3) yields the EOF name.
        We assert that the returned string preserves the pre-action and that the heredoc marker was added.
        """
        action = "pre\nSTART\ncmd\nEND\npost"
        # pattern has three capturing groups; group(3) will be "END\n" -> .strip() -> "END"
        pattern = re.compile(r"(START\n)(.*?\n)(END\n)", re.S)

        # call function under test
        result = _guard_multiline_input(action, lambda s: pattern.search(s))

        # The pre action should be preserved
        self.assertIn("pre", result)
        # The function attempts to append the heredoc marker using the EOF name from group(3)
        self.assertIn("<< 'END'", result)
