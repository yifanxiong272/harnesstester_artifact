import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.qlib.experiment.factor_experiment')
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
        """Verify QlibFactorExperiment sets up QlibFBWorkspace and stdout correctly."""
        # Patch the workspace's inject_code_from_folder to avoid filesystem operations
        with unittest.mock.patch.object(
            QlibFBWorkspace, "inject_code_from_folder", return_value=None
        ) as mock_inject:
            # Provide the required 'sub_tasks' argument to avoid Experiment.__init__ error
            exp = QlibFactorExperiment(sub_tasks=[])

            # The experiment should have an experiment_workspace of the right type
            self.assertIsInstance(exp.experiment_workspace, QlibFBWorkspace)

            # stdout should be initialized to an empty string
            self.assertEqual(exp.stdout, "")

            # Ensure inject_code_from_folder was called once and the argument ends with 'factor_template'
            mock_inject.assert_called_once()
            called_args = mock_inject.call_args[0]
            # The patched method will have been called with the template path as the first positional arg
            self.assertGreaterEqual(len(called_args), 1)
            template_path = called_args[0]
            # The template folder name should be 'factor_template'
            name = getattr(template_path, "name", None) or str(template_path).rstrip("/\\").split("/")[-1].split("\\")[-1]
            self.assertEqual(name, "factor_template")
