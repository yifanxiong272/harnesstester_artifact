import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.environment.repo')
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
        """repo_from_simplified_input returns a LocalRepoConfig when type='local'."""
        import tempfile
        from pathlib import Path

        # create a directory with spaces and an apostrophe to verify repo_name sanitization
        with tempfile.TemporaryDirectory() as td:
            repo_path = Path(td) / "my repo's"
            repo_path.mkdir()

            cfg = repo_from_simplified_input(input=str(repo_path), base_commit="deadbeef", type="local")

            # Basic checks that we got a local config with the requested base_commit
            self.assertEqual(cfg.type, "local")
            self.assertEqual(cfg.base_commit, "deadbeef")

            # Path should match the input path
            self.assertEqual(str(cfg.path), str(repo_path))

            # repo_name should replace spaces with '-' and remove apostrophes
            self.assertEqual(cfg.repo_name, "my-repos")
