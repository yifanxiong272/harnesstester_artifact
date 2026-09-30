import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.analytics')
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
        """Ensure enable() respects permanently_disable and calls disable(True)."""
        # Use a temporary directory under the current working directory so no external imports are needed
        tmp_home = Path.cwd() / ".aider_test_home"
        tmp_home.mkdir(parents=True, exist_ok=True)

        try:
            # Patch Path.home to our temporary directory
            with patch.object(Path, "home", lambda: tmp_home):
                analytics = Analytics()
                # A UUID should have been created
                self.assertIsNotNone(analytics.user_id)

                # Simulate permanent disable state so enable() should call disable(True)
                analytics.permanently_disable = True
                analytics.asked_opt_in = False

                # Put dummy providers to ensure disable clears them
                analytics.mp = object()
                analytics.ph = object()

                analytics.enable()

                # Providers should be cleared by disable(True)
                self.assertIsNone(analytics.mp)
                self.assertIsNone(analytics.ph)
                # permanently_disable remains True and asked_opt_in is set to True by disable(True)
                self.assertTrue(analytics.permanently_disable)
                self.assertTrue(analytics.asked_opt_in)
        finally:
            # Best-effort cleanup of created files/directories
            try:
                data_file = tmp_home / ".aider" / "analytics.json"
                if data_file.exists():
                    data_file.unlink()
                aider_dir = tmp_home / ".aider"
                if aider_dir.exists():
                    try:
                        aider_dir.rmdir()
                    except OSError:
                        # directory may not be empty; ignore
                        pass
                if tmp_home.exists():
                    try:
                        tmp_home.rmdir()
                    except OSError:
                        pass
            except Exception:
                pass
