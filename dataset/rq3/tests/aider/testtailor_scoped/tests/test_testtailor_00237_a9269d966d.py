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
        """Ensure get_windows_parent_process_name returns None when the immediate parent is None."""
        # Try to locate the function across the aider package and some likely modules.
        func = None
        tried = []
        candidates = [
            "aider.platform",
            "aider.system",
            "aider.utils",
            "aider",
            "aider.helpers",
            "aider.windows",
            "aider.platforms",
            "aider.platforms.windows",
        ]
        for mod in candidates:
            try:
                module = __import__(mod, fromlist=["*"])
                candidate = getattr(module, "get_windows_parent_process_name", None)
                if candidate:
                    func = candidate
                    break
            except Exception:
                tried.append(mod)
                continue

        # If not found yet, try importing submodules of the aider package and scanning sys.modules.
        if func is None:
            try:
                pkg = __import__("aider", fromlist=["*"])
            except Exception:
                pkg = None

            if pkg:
                # Try importing attributes as submodules (e.g., aider.xxx)
                for name in dir(pkg):
                    # skip private names
                    if name.startswith("_"):
                        continue
                    full = f"aider.{name}"
                    try:
                        sub = __import__(full, fromlist=["*"])
                        candidate = getattr(sub, "get_windows_parent_process_name", None)
                        if candidate:
                            func = candidate
                            break
                    except Exception:
                        continue

        if func is None:
            # Scan already-loaded modules as a last resort
            try:
                sys = __import__("sys")
                for m in list(sys.modules.values()):
                    try:
                        if hasattr(m, "get_windows_parent_process_name"):
                            func = getattr(m, "get_windows_parent_process_name")
                            break
                    except Exception:
                        continue
            except Exception:
                pass

        self.assertIsNotNone(func, "Could not find get_windows_parent_process_name in expected modules")

        # Patch psutil.Process so that parent() returns None on first call (loop executes once and breaks)
        with patch("psutil.Process") as mock_process_cls:
            mock_process = MagicMock()
            mock_process.parent.return_value = None
            mock_process_cls.return_value = mock_process

            result = func()
            self.assertIsNone(result)
