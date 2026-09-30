import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.utils.files')
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
        """Ensure load_file correctly parses .jsonl files, skipping empty/whitespace lines."""
        p = Path("test_sample.jsonl")
        try:
            # include valid JSON lines, an empty line and a whitespace-only line
            lines = ['{"a": 1}', '', '   ', '{"b": 2}', '{"c": [1, 2, 3]}']
            p.write_text("\n".join(lines))
            result = load_file(p)
            expected = [{"a": 1}, {"b": 2}, {"c": [1, 2, 3]}]
            self.assertEqual(result, expected)
        finally:
            # clean up the file created for the test
            try:
                p.unlink()
            except Exception:
                pass
