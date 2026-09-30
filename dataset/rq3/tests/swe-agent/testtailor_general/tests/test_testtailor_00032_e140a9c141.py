import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.quick_stats')
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
        """Test that quick_stats logs an error when a .traj file contains invalid JSON."""
        # Create a unique temporary directory under the current working directory
        tmp_path = Path.cwd() / f"tmp_quick_stats_test_{id(self)}"
        # Ensure a clean state
        if tmp_path.exists():
            for p in tmp_path.iterdir():
                try:
                    if p.is_file():
                        p.unlink()
                    else:
                        for sub in p.rglob('*'):
                            if sub.is_file():
                                sub.unlink()
                        p.rmdir()
                except Exception:
                    pass
            try:
                tmp_path.rmdir()
            except Exception:
                pass

        tmp_path.mkdir(parents=True, exist_ok=True)
        traj_file = tmp_path / "broken.traj"

        # Write invalid JSON to force json.loads to raise and hit the exception handler
        traj_file.write_text("this is not valid json {")

        try:
            result = quick_stats(tmp_path)
            # Since the file could not be processed, there should be no valid api_calls data
            self.assertEqual(result, "No valid api_calls data found in the .traj files.")
        finally:
            # Cleanup
            try:
                if traj_file.exists():
                    traj_file.unlink()
            except Exception:
                pass
            try:
                if tmp_path.exists():
                    tmp_path.rmdir()
            except Exception:
                pass
