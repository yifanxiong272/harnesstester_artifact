import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.remove_unfinished')
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
        """Directory with '__' but no .traj files logs 'No trajectories found'."""
        base_dir = Path.cwd() / "tmp_remove_unfinished_testdir"
        sub = base_dir / "example__001"
        try:
            # ensure clean start
            if base_dir.exists():
                # try removing if empty from previous runs
                try:
                    for p in base_dir.iterdir():
                        if p.is_dir():
                            for child in p.iterdir():
                                child.unlink()
                            p.rmdir()
                    base_dir.rmdir()
                except Exception:
                    pass
            base_dir.mkdir()
            sub.mkdir()
            # Patch logger.info to assert the specific message is emitted
            with unittest.mock.patch.object(logger, "info") as mock_info:
                remove_unfinished(base_dir, dry_run=True)
                mock_info.assert_any_call("No trajectories found in %s", sub)
        finally:
            # cleanup
            try:
                if sub.exists():
                    sub.rmdir()
                if base_dir.exists():
                    base_dir.rmdir()
            except Exception:
                pass
