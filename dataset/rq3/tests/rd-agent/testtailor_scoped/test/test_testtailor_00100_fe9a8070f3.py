import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.log.utils.__init__')
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
        """is_valid_session should be True only for a directory that contains a '__session__' entry."""
        import tempfile
        from pathlib import Path

        # Create a temporary directory to hold test cases
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)

            # Case 1: directory with __session__ -> True
            sess_dir = base / "session_ok"
            sess_dir.mkdir()
            (sess_dir / "__session__").write_text("marker")
            assert is_valid_session(sess_dir) is True

            # Case 2: directory without __session__ -> False
            no_sess_dir = base / "session_no"
            no_sess_dir.mkdir()
            assert is_valid_session(no_sess_dir) is False

            # Case 3: path is a file (not a directory) even if named __session__ -> False
            file_path = base / "some_file"
            file_path.write_text("data")
            assert is_valid_session(file_path) is False

            # Case 4: directory with a different file -> False
            other_dir = base / "other"
            other_dir.mkdir()
            (other_dir / "not_session").write_text("x")
            assert is_valid_session(other_dir) is False
