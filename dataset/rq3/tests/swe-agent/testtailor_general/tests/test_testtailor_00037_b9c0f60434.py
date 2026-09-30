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
        """Test that problem_statement_from_simplified_input returns a TextProblemStatement when type is 'text'."""
        input_text = "Example problem statement text."
        ps = problem_statement_from_simplified_input(input=input_text, type="text")

        # Should be the correct model type
        self.assertIsInstance(ps, TextProblemStatement)

        # Problem statement text should match input
        self.assertEqual(ps.get_problem_statement(), input_text)

        # id should be set to the first 6 chars of the sha256 hash of the text
        expected_id = hashlib.sha256(input_text.encode()).hexdigest()[:6]
        self.assertEqual(ps.id, expected_id)

        # type discriminator and extra fields
        self.assertEqual(ps.type, "text")
        self.assertEqual(ps.get_extra_fields(), {})
