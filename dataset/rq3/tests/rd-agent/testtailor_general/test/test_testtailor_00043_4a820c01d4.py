import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.data_science.proposal.exp_gen.idea_pool')
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
        """Ensure DSIdea correctly handles raw_knowledge provided as a JSON string."""
        raw = (
            '{"idea": "Test Idea",'
            ' "method": "test method",'
            ' "context": "test context",'
            ' "hypothesis": {"scenario_problem": "scen", "feedback_problem": "feed"},'
            ' "competition": "comp"}'
        )
        d = DSIdea(raw)
        # Attributes loaded from the JSON string
        self.assertEqual(d.idea, "Test Idea")
        self.assertEqual(d.method, "test method")
        self.assertEqual(d.context, "test context")
        self.assertEqual(d.competition, "comp")
        # Hypothesis should be a dict and contain expected keys/values
        self.assertIsInstance(d.hypothesis, dict)
        self.assertEqual(d.hypothesis.get("scenario_problem"), "scen")
        self.assertEqual(d.hypothesis.get("feedback_problem"), "feed")
        # __str__ should return a JSON-like string containing the idea and competition
        s = str(d)
        self.assertIn('"idea"', s)
        self.assertIn("Test Idea", s)
        self.assertIn('"competition"', s)
        self.assertIn("comp", s)
