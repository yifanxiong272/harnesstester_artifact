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
        """Ensure _norm strips only trailing CR characters and leaves other characters (including LF) intact."""
        samples = {
            "abc": "abc",                 # no CR
            "abc\r": "abc",               # single trailing CR removed
            "abc\r\r": "abc",             # multiple trailing CRs removed
            "\r": "",                     # only CR -> empty
            "\r\r": "",                   # multiple CRs -> empty
            "": "",                       # empty stays empty
            "abc\r\n": "abc\r\n",         # CRLF should remain (only CR at very end removed, here LF is last)
            "line\n": "line\n",           # only LF should remain untouched
            "a\rb\r": "a\rb",             # internal CRs preserved, trailing CR removed
        }

        for inp, expected in samples.items():
            result = _norm(inp)
            self.assertIsInstance(result, str)
            self.assertEqual(result, expected, msg=f"Failed for input repr({inp!r}) -> got {result!r}, expected {expected!r}")
