import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.tools.pr_help_message')
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
        """complete the test case here"""
        column_arr_1 = ["Tool1", "Tool2", "Tool3"]
        column_arr_2 = ["Desc1"]
        result = generate_bbdc_table(column_arr_1, column_arr_2)
        expected = (
            "| Tool  | Description | \n"
            "|--|--|\n"
            "| Tool1 | Desc1 |\n"
            "| Tool2 |  |\n"
            "| Tool3 |  |\n"
        )
        self.assertEqual(result, expected)
