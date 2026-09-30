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
        """When the JSON 'learnings' list contains plain strings (not objects),
        the code should take the branch that treats each item as a non-dict:
        learning = str(item).strip() and citation = "".
        """
        response = '{"learnings": ["Simple insight"], "followUpQuestions": ["Why?"], "extra": 1}'
        result = parse_research_results_response(response, num_learnings=3)

        expected = {
            "learnings": ["Simple insight"],
            "followUpQuestions": ["Why?"],
            "citations": {},
        }

        self.assertEqual(result, expected)
