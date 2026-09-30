import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.utils.memory_monitor')
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
        """Logger should be called with stripped message when message is non-empty and not just whitespace."""
        stream = LogStream()
        module = __import__(LogStream.__module__, fromlist=['*'])
        had_logger = hasattr(module, 'logger')
        orig_logger = getattr(module, 'logger', None)
        try:
            mock_logger = unittest.mock.MagicMock()
            setattr(module, 'logger', mock_logger)

            message = "   123 KB\n"
            stream.write(message)

            mock_logger.info.assert_called_once_with('[Memory usage] 123 KB')
        finally:
            if had_logger:
                setattr(module, 'logger', orig_logger)
            else:
                try:
                    delattr(module, 'logger')
                except Exception:
                    pass
