import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.config')
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
        """If the init (PID 1) command line contains 'py'/'uv'/'app', is_running_in_docker() returns True."""
        class DummyProc:
            def cmdline(self):
                # join -> "python something" contains "py"
                return ["python", "app.py"]

        # Ensure earlier filesystem checks don't short-circuit to True, and ensure pid count check is False.
        with unittest.mock.patch.object(Path, "exists", return_value=False), \
             unittest.mock.patch.object(Path, "read_text", return_value=""), \
             unittest.mock.patch.object(psutil, "Process", return_value=DummyProc()), \
             unittest.mock.patch.object(psutil, "pids", return_value=list(range(100))):
            self.assertTrue(is_running_in_docker())
