import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.environment.hooks.status')
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
        """Verify SetStatusEnvironmentHook.on_install_env_started calls the provided callable with expected message."""
        calls = []

        def recorder(_id, message):
            calls.append((_id, message))

        hook = SetStatusEnvironmentHook("env123", recorder)
        hook.on_install_env_started()

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], ("env123", "Installing environment"))
