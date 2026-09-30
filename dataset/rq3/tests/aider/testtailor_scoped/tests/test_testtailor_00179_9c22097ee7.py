import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.run_cmd')
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
        """Ensure get_windows_parent_process_name walks parent chain and finds powershell.exe"""
        # Patch psutil.Process so the function under test uses our mock process chain
        with patch("psutil.Process") as mock_proc_class:
            # Create the current process mock and a chain of parents
            current = MagicMock()
            parent1 = MagicMock()
            parent2 = MagicMock()

            # current -> parent1 -> parent2 -> None
            mock_proc_class.return_value = current
            current.parent.return_value = parent1
            parent1.parent.return_value = parent2
            parent2.parent.return_value = None

            # parent2 reports the name "PowerShell.exe" (function lowercases names)
            parent2.name.return_value = "PowerShell.exe"
            parent1.name.return_value = "someprocess.exe"
            current.name.return_value = "child.exe"

            # Attempt to locate the function in loaded modules (robust to module path)
            func = None
            import sys
            import importlib

            # First look through already loaded modules for the function
            for mod in list(sys.modules.values()):
                try:
                    if hasattr(mod, "get_windows_parent_process_name"):
                        func = getattr(mod, "get_windows_parent_process_name")
                        break
                except Exception:
                    continue

            # If not found, try a few likely module names
            if func is None:
                candidates = (
                    "aider", "aider.utils", "aider.helpers", "aider.windows", "aider._compat"
                )
                for name in candidates:
                    try:
                        mod = importlib.import_module(name)
                        if hasattr(mod, "get_windows_parent_process_name"):
                            func = getattr(mod, "get_windows_parent_process_name")
                            break
                    except Exception:
                        continue

            self.assertIsNotNone(func, "Could not find get_windows_parent_process_name in project modules")

            # Call the function; it should traverse parents and return the lowercase parent name
            result = func()
            self.assertEqual(result, "powershell.exe")
