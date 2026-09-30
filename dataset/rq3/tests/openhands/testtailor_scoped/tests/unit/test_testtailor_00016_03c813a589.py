import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.impl.action_execution.action_execution_client')
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
        """Locate _is_retryable_error in the openhands package and verify its behavior."""
        import os
        import importlib
        import openhands

        func = None
        pkg_name = openhands.__name__
        # Search package files for the function definition (fast, no heavy imports)
        for pkg_path in openhands.__path__:
            for root, _, files in os.walk(pkg_path):
                for fname in files:
                    if not fname.endswith(".py"):
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as fh:
                            content = fh.read()
                    except OSError:
                        continue
                    if "def _is_retryable_error" in content:
                        # compute module name
                        rel = os.path.relpath(fpath, pkg_path)
                        if rel == "__init__.py":
                            module_name = pkg_name
                        else:
                            mod_part = rel[:-3].replace(os.sep, ".")
                            module_name = pkg_name + "." + mod_part
                        try:
                            module = importlib.import_module(module_name)
                        except Exception:
                            # If importing this module fails, continue searching
                            continue
                        func = getattr(module, "_is_retryable_error", None)
                        if func is not None:
                            break
                if func is not None:
                    break
            if func is not None:
                break

        self.assertIsNotNone(func, "_is_retryable_error not found in openhands package")

        # Import exception classes and exercise the function
        import httpx
        import httpcore

        retryable_httpx = httpx.RemoteProtocolError("httpx remote protocol")
        retryable_httpcore = httpcore.RemoteProtocolError("httpcore remote protocol")
        not_retryable = RuntimeError("not retryable")

        self.assertTrue(func(retryable_httpx))
        self.assertTrue(func(retryable_httpcore))
        self.assertFalse(func(not_retryable))
