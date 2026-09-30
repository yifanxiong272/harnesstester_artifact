import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.components.coder.data_science.utils')
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
        """remove_eda_part removes EDA block(s) and leaves other text intact"""
        # single EDA block with newlines inside
        stdout1 = (
            "Line1\n"
            "=== Start of EDA part ===\n"
            "EDA content line A\n"
            "EDA content line B\n"
            "=== End of EDA part ===\n"
            "Line2"
        )
        res1 = remove_eda_part(stdout1)
        # the content between the markers (including the markers) is removed;
        # the newline before the start marker and the newline after the end marker remain,
        # so there will be two newlines between Line1 and Line2
        self.assertEqual(res1, "Line1\n\nLine2")

        # no EDA markers -> string unchanged
        stdout2 = "No EDA here\nJust regular output"
        res2 = remove_eda_part(stdout2)
        self.assertEqual(res2, stdout2)

        # multiple EDA blocks: regex is greedy, so it will remove from the first start
        # to the last end in one removal
        stdout3 = (
            "A\n"
            "=== Start of EDA part ===\n"
            "foo\n"
            "=== End of EDA part ===\n"
            "B\n"
            "=== Start of EDA part ===\n"
            "bar\n"
            "=== End of EDA part ===\n"
            "C"
        )
        res3 = remove_eda_part(stdout3)
        # everything from the first start to the last end is removed; leaves A and C separated by two newlines
        self.assertEqual(res3, "A\n\nC")
