import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.integrations.gmail.service')
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
        """Passing a non-None config_dir results in config_dir being expanded/resolved to a Path"""
        config_dir_str = '~/__gmail_service_test_config__'
        resolved_path = Path(config_dir_str).expanduser().resolve()

        # Ensure a clean start: if the path exists and is an empty dir, remove it.
        if resolved_path.exists() and resolved_path.is_dir():
            try:
                resolved_path.rmdir()
            except Exception:
                # If it's not empty or can't be removed, proceed anyway; test should still exercise the code path.
                pass

        try:
            service = GmailService(config_dir=config_dir_str)
            # The service.config_dir should be a Path and should equal the resolved config_dir path
            self.assertIsInstance(service.config_dir, Path)
            self.assertEqual(service.config_dir, resolved_path)
        finally:
            # Cleanup: remove the directory if it was created and is empty
            try:
                if resolved_path.exists() and resolved_path.is_dir():
                    resolved_path.rmdir()
            except Exception:
                pass
