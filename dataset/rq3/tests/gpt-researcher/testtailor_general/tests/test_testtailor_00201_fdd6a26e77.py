import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('gpt_researcher.skills.deep_research')
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
        """Ensure non-dict items in the JSON learnings list are handled via str(item).strip()."""
        response = '{"learnings": ["  Notable event  "], "followUpQuestions": ["  What next?  "]}'
        result = parse_research_results_response(response, num_learnings=2)

        self.assertIsInstance(result, dict)
        self.assertEqual(result["learnings"], ["Notable event"])
        self.assertEqual(result["followUpQuestions"], ["What next?"])
        self.assertEqual(result["citations"], {})
