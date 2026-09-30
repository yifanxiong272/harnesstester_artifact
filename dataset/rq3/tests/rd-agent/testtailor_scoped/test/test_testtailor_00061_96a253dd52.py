import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.storage')
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
        """Ensure _remove_empty_dir removes empty subdirectories but keeps non-empty ones."""
        # import needed modules here to avoid relying on top-level imports
        import sys
        import importlib
        import tempfile
        from pathlib import Path

        # create a temporary directory structure
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dir_a = root / "dir_a"
            dir_a_sub = dir_a / "empty_sub"
            dir_b = root / "dir_b"
            # make directories
            dir_a_sub.mkdir(parents=True)
            dir_b.mkdir(parents=True)
            # put a file into dir_b so it's non-empty
            (dir_b / "keep.txt").write_text("keep this")

            # sanity checks before invoking function
            self.assertTrue(dir_a.exists() and dir_a.is_dir())
            self.assertTrue(dir_a_sub.exists() and dir_a_sub.is_dir())
            self.assertTrue(dir_b.exists() and dir_b.is_dir())
            self.assertTrue((dir_b / "keep.txt").exists())

            # try to locate and call the _remove_empty_dir function from loaded modules
            fn = None
            # search already-imported modules first
            for mname, mod in list(sys.modules.items()):
                try:
                    if mod and hasattr(mod, "_remove_empty_dir"):
                        fn = getattr(mod, "_remove_empty_dir")
                        break
                except Exception:
                    continue

            # try some likely module locations if not found yet
            if fn is None:
                candidates = [
                    "rdagent.app.utils",
                    "rdagent.utils",
                    "rdagent",
                    "rdagent.app",
                    "rdagent.lib",
                ]
                for cand in candidates:
                    try:
                        mod = importlib.import_module(cand)
                        if hasattr(mod, "_remove_empty_dir"):
                            fn = getattr(mod, "_remove_empty_dir")
                            break
                    except Exception:
                        continue

            self.assertIsNotNone(fn, "_remove_empty_dir function not found in inspected modules")

            # call the function under test
            fn(root)

            # after removal: dir_a and its empty subdir should be gone; dir_b should remain
            self.assertFalse(dir_a_sub.exists(), "empty subdirectory should have been removed")
            self.assertFalse(dir_a.exists(), "directory that became empty should have been removed")
            self.assertTrue(dir_b.exists(), "non-empty directory should remain")
            self.assertTrue((dir_b / "keep.txt").exists(), "file in non-empty directory should remain")
