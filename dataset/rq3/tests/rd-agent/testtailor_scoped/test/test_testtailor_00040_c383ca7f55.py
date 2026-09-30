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
        """complete the test case here"""
        raw_dict = {
            "competition": "comp-name",
            "idea": "Test Idea",
            "method": "A general method description",
            "context": "Example context description",
            "hypothesis": {
                "scenario_problem": "classification task",
                "feedback_problem": "imbalanced classes",
            },
        }
        raw_str = json.dumps(raw_dict)

        ds = DSIdea(raw_str)

        # basic attribute checks
        self.assertEqual(ds.competition, raw_dict["competition"])
        self.assertEqual(ds.idea, raw_dict["idea"])
        self.assertEqual(ds.method, raw_dict["method"])
        self.assertEqual(ds.context, raw_dict["context"])
        self.assertEqual(ds.hypothesis, raw_dict["hypothesis"])

        # ensure hypothesis stored is independent (original dict mutation shouldn't affect ds.hypothesis)
        raw_dict["hypothesis"]["scenario_problem"] = "changed"
        self.assertNotEqual(ds.hypothesis["scenario_problem"], raw_dict["hypothesis"]["scenario_problem"])
