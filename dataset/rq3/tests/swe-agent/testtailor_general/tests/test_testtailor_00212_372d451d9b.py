import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.agent.problem_statement')
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
        """Ensure __str__ returns id and first 30 chars of text followed by ellipsis."""
        # long text (>30 chars) to trigger truncation
        long_text = "abcdefghijklmnopqrstuvwxyz0123456789EXTRA"
        tp = TextProblemStatement(text=long_text, id="id123")
        result = str(tp)
        expected = f"id={tp.id}, text={tp.text[:30]}..."
        self.assertEqual(result, expected)
