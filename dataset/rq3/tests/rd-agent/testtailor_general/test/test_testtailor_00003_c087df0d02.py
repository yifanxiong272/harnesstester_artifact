import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.ui.utils')
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
        """Write a temp file with timestamps on the first and last lines and
        ensure get_script_time returns the correct timedelta (10 seconds)."""
        p = Path("tmp_test_get_script_time.log")
        try:
            with p.open("w", encoding="utf-8") as f:
                # first line with timestamp
                f.write("2022-07-01 12:00:00+00:00 start\n")
                # middle line to ensure deque reads the last line, not the one just read
                f.write("some intermediate log line\n")
                # last line with timestamp 10 seconds later
                f.write("2022-07-01 12:00:10+00:00 end\n")

            result = get_script_time(p)
            self.assertIsNotNone(result)
            # result is a pandas Timedelta; check seconds difference is 10
            self.assertEqual(result.total_seconds(), 10.0)
        finally:
            try:
                p.unlink()
            except Exception:
                pass
