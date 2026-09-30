import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.hooks.apply_patch')
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
        """Ensure _apply_patch builds the git apply command and calls subprocess.run with correct cwd."""
        # Create a directory in the current working directory to avoid using tempfile
        base = Path.cwd() / "test_apply_patch_dir"
        # Clean up any previous run leftovers if present
        if base.exists():
            for p in base.iterdir():
                if p.is_file():
                    p.unlink()
                elif p.is_dir():
                    for q in p.iterdir():
                        if q.is_file():
                            q.unlink()
                    p.rmdir()
            if base.exists():
                base.rmdir()
        base.mkdir()
        try:
            local_dir = base
            # create a patch file inside the directory
            patch_file = local_dir / "example.patch"
            patch_file.write_text("dummy patch content")

            # sanity checks to hit the asserts in the target code
            assert local_dir.is_dir()
            assert patch_file.exists()

            hook = SaveApplyPatchHook()

            # Patch subprocess.run so we don't actually invoke git
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
                hook._apply_patch(patch_file, local_dir)

                expected_cmd = ["git", "apply", str(patch_file.resolve())]
                mock_run.assert_called_once_with(expected_cmd, cwd=local_dir, check=True)
        finally:
            # cleanup created files and directory
            try:
                if patch_file.exists():
                    patch_file.unlink()
                if local_dir.exists():
                    local_dir.rmdir()
            except Exception:
                # best-effort cleanup; ignore errors here
                pass
