import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.developer.coder')
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
        """Ensure KGModelFeatureSelectionCoder.develop injects selection code when a single data_description exists."""
        # Ensure a known mapping exists for the test
        try:
            KG_SELECT_MAPPING.clear()
        except Exception:
            pass
        KG_SELECT_MAPPING["dummy_model"] = "select.py"

        # create a minimal sub_task with required attribute
        subtask = type("SubTask", (), {"model_type": "dummy_model"})()

        # create a minimal workspace implementing only what develop() needs
        class DummyWorkspace:
            def __init__(self):
                # ensure length == 1 to take the simple branch (no LLM call)
                self.data_description = [("Original features", 5)]
                self.file_dict = {}

            def inject_files(self, **kwargs):
                # store injected files so assertions can inspect them
                self.file_dict.update(kwargs)

        # create a minimal experiment object with attributes used by develop()
        exp = type("Exp", (), {})()
        exp.sub_tasks = [subtask]
        exp.experiment_workspace = DummyWorkspace()
        # scen is not used for the single-data_description branch, but provide a stub
        exp.scen = type("Sc", (), {"get_scenario_all_desc": lambda self: {"name": "dummy"}})()

        # Developer base class requires a scen parameter in constructor; provide a minimal stub
        coder = KGModelFeatureSelectionCoder(type("ScenStub", (), {})())
        result = coder.develop(exp)

        # verify develop returned the same experiment and injected the expected file
        self.assertIs(result, exp)
        self.assertIn("select.py", exp.experiment_workspace.file_dict)
        injected_code = exp.experiment_workspace.file_dict["select.py"]
        # basic sanity checks on the generated code
        self.assertIsInstance(injected_code, str)
        self.assertIn("def select", injected_code)
        self.assertIn("return X", injected_code)
