import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.data_science.scen.utils')
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
        """Ensure plaintext files are counted by lines, and returned string is correct."""
        # create a unique filename based on the test instance id to avoid clashes
        p = Path(f"test_sample_{id(self)}.txt")
        p.write_text("first line\nsecond line\nthird line\n")
        try:
            num, human = get_file_len_size(p)
            self.assertEqual(num, 3)
            self.assertEqual(human, "3 lines")
        finally:
            try:
                p.unlink()
            except Exception:
                pass
