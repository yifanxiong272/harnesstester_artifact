import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_description')
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
        """Exercise branch where a word equals the literal '<br>' so is_saved_word becomes True."""
        # craft input so that after splitting by '<br>' there is an empty line -> yields a standalone '<br>' word
        a_seq = 'a' * 71
        b_seq = 'b' * 10
        text = a_seq + '<br><br>' + b_seq

        result = insert_br_after_x_chars(text)

        expected = '<br>' + a_seq + '<br> <br> ' + b_seq
        self.assertEqual(result, expected)
