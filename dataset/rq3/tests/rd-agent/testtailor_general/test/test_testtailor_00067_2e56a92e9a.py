import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.server.debug_app')
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
        """Locate the favicon function, patch send_from_directory and assert it is called correctly."""
        import sys
        import inspect
        import unittest as _unittest

        # Find the loaded module that defines a favicon() function which uses send_from_directory
        favicon_func = None
        target_module = None
        for mod in list(sys.modules.values()):
            if not mod:
                continue
            if hasattr(mod, "favicon"):
                cand = getattr(mod, "favicon")
                if inspect.isfunction(cand):
                    try:
                        src = inspect.getsource(cand)
                    except (OSError, TypeError):
                        continue
                    if "send_from_directory" in src:
                        favicon_func = cand
                        target_module = sys.modules[cand.__module__]
                        break

        self.assertIsNotNone(favicon_func, "Could not locate a favicon() function using send_from_directory")
        self.assertIsNotNone(target_module, "Target module for favicon() not found")
        self.assertTrue(hasattr(target_module, "app"), "Target module does not expose 'app'")

        static_folder = getattr(target_module, "app").static_folder

        # Patch send_from_directory in the target module and verify the call and return value
        with _unittest.mock.patch.object(target_module, "send_from_directory") as mock_sfd:
            mock_sfd.return_value = "SENTINEL_RESPONSE"
            result = favicon_func()
            self.assertEqual(result, "SENTINEL_RESPONSE")
            mock_sfd.assert_called_once_with(static_folder, "favicon.ico", mimetype="image/vnd.microsoft.icon")
