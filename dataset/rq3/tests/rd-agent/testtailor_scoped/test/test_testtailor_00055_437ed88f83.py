import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.data_science.dev.feedback')
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
        """Ensure DSExperiment2Feedback initializes and sets version properly."""
        class SimpleScenario(Scenario):
            @property
            def background(self):
                return "simple background"

            @property
            def rich_style_description(self):
                return "rich description"

            def get_scenario_all_desc(self, task=None, filtered_tag=None, simple_background=None):
                return "combined scenario description"

            def get_runtime_environment(self):
                return "runtime env"

        scen = SimpleScenario()
        inst = DSExperiment2Feedback(scen, version="exp_feedback_test")

        # Check that constructor set the version and stored the scenario via super().__init__
        self.assertEqual(inst.version, "exp_feedback_test")
        self.assertIs(getattr(inst, "scen", None), scen)
