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
        """Locate and exercise _is_retryable_error by scanning package files (no heavy imports)."""
        import os
        import importlib
        import openhands

        func = None
        pkg_paths = list(getattr(openhands, "__path__", []))
        # Fallback to dirname of package file if __path__ not present
        if not pkg_paths and hasattr(openhands, "__file__"):
            pkg_paths = [os.path.dirname(openhands.__file__)]

        for pkg_path in pkg_paths:
            for dirpath, _, filenames in os.walk(pkg_path):
                # Check only a few files to stay fast
                for fname in filenames:
                    if not fname.endswith(".py"):
                        continue
                    fpath = os.path.join(dirpath, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as fh:
                            src = fh.read()
                    except Exception:
                        continue
                    if "def _is_retryable_error" in src:
                        # derive module name from file path
                        rel = os.path.relpath(fpath, pkg_path)
                        mod_name = rel[:-3].replace(os.path.sep, ".")  # strip .py
                        if mod_name.endswith(".__init__"):
                            mod_name = mod_name[: -len(".__init__")]
                        full_mod = f"{openhands.__name__}.{mod_name}" if mod_name else openhands.__name__
                        try:
                            module = importlib.import_module(full_mod)
                        except Exception:
                            # try importing the package root if module import fails
                            try:
                                module = importlib.import_module(openhands.__name__)
                            except Exception:
                                continue
                        if hasattr(module, "_is_retryable_error"):
                            func = getattr(module, "_is_retryable_error")
                            break
                if func is not None:
                    break
            if func is not None:
                break

        # As a last resort, check package root
        if func is None and hasattr(openhands, "_is_retryable_error"):
            func = getattr(openhands, "_is_retryable_error")

        self.assertIsNotNone(func, "_is_retryable_error not found in openhands package")

        import httpx
        import httpcore

        e_httpx = httpx.RemoteProtocolError("simulated")
        e_httpcore = httpcore.RemoteProtocolError("simulated")
        self.assertTrue(func(e_httpx), "httpx.RemoteProtocolError should be retryable")
        self.assertTrue(func(e_httpcore), "httpcore.RemoteProtocolError should be retryable")
        self.assertFalse(func(Exception("other")), "Generic Exception should not be retryable")
