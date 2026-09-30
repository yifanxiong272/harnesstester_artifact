import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.voice')
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
        """When importing sounddevice raises ModuleNotFoundError, __init__ should raise SoundDeviceError from the except branch."""
        # Ensure sf is not None so we don't hit the early return that raises SoundDeviceError
        with patch("aider.voice.sf", MagicMock()):
            import builtins

            orig_import = builtins.__import__

            def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
                # Only simulate missing module for 'sounddevice'
                if name == "sounddevice":
                    raise ModuleNotFoundError("No module named 'sounddevice'")
                return orig_import(name, globals, locals, fromlist, level)

            with patch("builtins.__import__", side_effect=fake_import):
                with self.assertRaises(SoundDeviceError):
                    Voice()
