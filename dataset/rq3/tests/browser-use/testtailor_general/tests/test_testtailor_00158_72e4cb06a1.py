import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.mcp.server')
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
        """When PSUTIL_AVAILABLE is False, get_parent_process_cmdline() must return None."""
        import sys
        import inspect

        # Find the module that defines get_parent_process_cmdline
        target_module = None
        for mod in list(sys.modules.values()):
            if not mod:
                continue
            try:
                attr = getattr(mod, "get_parent_process_cmdline", None)
            except Exception:
                continue
            if inspect.isfunction(attr) or inspect.ismethod(attr):
                # Found candidate
                target_module = mod
                break

        self.assertIsNotNone(target_module, "Couldn't find module defining get_parent_process_cmdline")

        # Backup original PSUTIL_AVAILABLE if present
        sentinel = object()
        original_value = getattr(target_module, "PSUTIL_AVAILABLE", sentinel)

        try:
            # Force the branch: not PSUTIL_AVAILABLE -> True
            setattr(target_module, "PSUTIL_AVAILABLE", False)

            # Call the function and assert it returns None
            result = target_module.get_parent_process_cmdline()
            self.assertIsNone(result, "Expected None when PSUTIL_AVAILABLE is False")
        finally:
            # Restore original state
            if original_value is sentinel:
                # It didn't exist before; remove it if present
                try:
                    delattr(target_module, "PSUTIL_AVAILABLE")
                except Exception:
                    # Some modules may not allow deletion; ignore
                    pass
            else:
                setattr(target_module, "PSUTIL_AVAILABLE", original_value)
