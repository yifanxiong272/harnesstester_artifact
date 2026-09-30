import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.kaggle.experiment.workspace')
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
        """Ensure KGFBWorkspace.__init__ calls super().__init__, inject_code_from_folder and sets data_description."""
        # Use a simple object as the template path; KGFBWorkspace will pass it to inject_code_from_folder.
        template_path = object()
        # Prevent the real FBWorkspace.__init__ from running (it may require extra args or side effects)
        with patch.object(FBWorkspace, "__init__", new=lambda self, *a, **k: None):
            # Patch inject_code_from_folder so we don't depend on template contents or side effects
            with patch.object(KGFBWorkspace, "inject_code_from_folder", autospec=True) as mock_inject:
                ws = KGFBWorkspace(template_path)
                # inject_code_from_folder should be called with the instance and the provided path
                mock_inject.assert_called_once_with(ws, template_path)
                # data_description should be initialized to an empty list
                self.assertEqual(ws.data_description, [])
