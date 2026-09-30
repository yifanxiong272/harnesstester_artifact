import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.scenarios.qlib.experiment.workspace')
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
        """Ensure QlibFBWorkspace calls its parent __init__ with forwarded args/kwargs
        and then calls inject_code_from_folder with the provided template path.
        """
        # create a unique temporary directory name without relying on tempfile
        template_path = Path(f"tmp_test_dir_{id(self)}")
        # ensure folder exists
        if template_path.exists():
            # if exists and is a dir, try to remove then recreate to have a clean state
            try:
                template_path.rmdir()
            except Exception:
                pass
        template_path.mkdir(exist_ok=True)

        called = {}
        # Save originals to restore later
        original_fb_init = FBWorkspace.__init__
        original_inject = QlibFBWorkspace.inject_code_from_folder

        try:
            # Replace FBWorkspace.__init__ to capture args and kwargs
            def fake_fb_init(self, *args, **kwargs):
                called['fb_init'] = (args, kwargs)
                # do minimal setup to avoid AttributeErrors later
                return None

            # Replace inject_code_from_folder to capture the path passed
            def fake_inject(self, path):
                called['inject'] = path
                return None

            FBWorkspace.__init__ = fake_fb_init
            QlibFBWorkspace.inject_code_from_folder = fake_inject

            # Instantiate with extra positional and keyword arguments
            obj = QlibFBWorkspace(template_path, 1, test='x')

            # Verify the parent __init__ was called with the forwarded args/kwargs
            self.assertIn('fb_init', called, "FBWorkspace.__init__ was not called")
            self.assertEqual(called['fb_init'][0], (1,))
            self.assertEqual(called['fb_init'][1], {'test': 'x'})

            # Verify inject_code_from_folder was called with the template path
            self.assertIn('inject', called, "inject_code_from_folder was not called")
            self.assertEqual(called['inject'], template_path)

        finally:
            # Restore originals and cleanup
            FBWorkspace.__init__ = original_fb_init
            QlibFBWorkspace.inject_code_from_folder = original_inject
            try:
                template_path.rmdir()
            except Exception:
                # best effort cleanup
                pass
