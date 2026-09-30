import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.qlib.experiment.quant_experiment')
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
        """Test that QlibFactorExperiment sets experiment_workspace to a QlibFBWorkspace
        instantiated with the expected template_folder_path (ends with 'factor_template')."""
        # Patch the parent FactorExperiment.__init__ so QlibFactorExperiment.__init__ can call super() safely
        with patch.object(FactorExperiment, "__init__", lambda self, *a, **k: None):
            captured = {"args": None, "kwargs": None}

            # Replace QlibFBWorkspace.__init__ to capture the template_folder_path passed in
            def fake_qfb_init(self, *args, **kwargs):
                captured["args"] = args
                captured["kwargs"] = kwargs
                # Do not perform any real initialization
                return None

            with patch.object(QlibFBWorkspace, "__init__", fake_qfb_init):
                # Instantiate the class under test; this should trigger the assignment:
                # self.experiment_workspace = QlibFBWorkspace(template_folder_path=...)
                inst = QlibFactorExperiment()

        # Verify that the attribute was created and is an instance of QlibFBWorkspace
        self.assertTrue(hasattr(inst, "experiment_workspace"))
        self.assertIsInstance(inst.experiment_workspace, QlibFBWorkspace)

        # Extract the captured template_folder_path (could be passed as kwarg or as first positional arg)
        tpl = None
        if captured.get("kwargs"):
            tpl = captured["kwargs"].get("template_folder_path")
        if tpl is None and captured.get("args"):
            # if positional, assume first arg is the template_folder_path
            tpl = captured["args"][0] if len(captured["args"]) > 0 else None

        self.assertIsNotNone(tpl, "template_folder_path was not passed to QlibFBWorkspace.__init__")
        # Normalize to a Path for robust comparison
        tpl_path = Path(tpl) if not isinstance(tpl, Path) else tpl
        # Ensure the folder name is the expected template folder
        self.assertEqual(tpl_path.name, "factor_template")
