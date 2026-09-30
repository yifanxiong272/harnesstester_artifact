import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.qlib.experiment.model_experiment')
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
        # Access the QlibModelExperiment class assumed to be imported in the test environment
        # and patch its base __init__ and the module-level QlibFBWorkspace to avoid heavy initialization.
        QME = QlibModelExperiment  # Provided by the test environment imports

        # Create a dummy workspace to capture the template_folder_path passed in
        captured = {}
        class DummyWorkspace:
            def __init__(self, template_folder_path: Path, *a, **kw):
                captured['template_folder_path'] = template_folder_path

        # Save originals to restore later
        base_cls = QME.__mro__[1]  # the immediate superclass (ModelExperiment)
        orig_base_init = getattr(base_cls, "__init__", None)

        # Patch the base __init__ to be a no-op to avoid requiring its real constructor args
        def noop_init(self, *a, **kw):
            return None

        base_cls.__init__ = noop_init

        # Patch the module-level QlibFBWorkspace symbol where QlibModelExperiment is defined
        import importlib, sys
        mod = importlib.import_module(QME.__module__)
        orig_workspace = getattr(mod, "QlibFBWorkspace", None)
        setattr(mod, "QlibFBWorkspace", DummyWorkspace)

        try:
            # Instantiate without invoking the real heavy base init (we patched it)
            inst = object.__new__(QME)
            inst.__init__()  # call the target __init__

            # Verify that experiment_workspace was set to our DummyWorkspace via the patched symbol
            self.assertIn('template_folder_path', captured, "QlibFBWorkspace was not constructed")
            expected_path = Path(mod.__file__).parent / "model_template"
            self.assertEqual(captured['template_folder_path'], expected_path)

            # Verify stdout was initialized to an empty string
            self.assertTrue(hasattr(inst, "stdout"))
            self.assertEqual(inst.stdout, "")

        finally:
            # Restore patched attributes to avoid side effects on other tests
            base_cls.__init__ = orig_base_init
            if orig_workspace is not None:
                setattr(mod, "QlibFBWorkspace", orig_workspace)
            else:
                delattr(mod, "QlibFBWorkspace")
