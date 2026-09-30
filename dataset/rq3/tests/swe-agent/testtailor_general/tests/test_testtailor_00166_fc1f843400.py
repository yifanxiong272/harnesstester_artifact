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
        """Ensure that when a promising patch is produced and apply_patch_locally is True,
        the hook resolves the local repo path and calls _apply_patch with the patch file and repo dir.
        """
        # Create temporary directories for output and a fake local repo
        import tempfile
        from types import SimpleNamespace
        from pathlib import Path

        with tempfile.TemporaryDirectory() as out_dir, tempfile.TemporaryDirectory() as repo_dir:
            out_path = Path(out_dir)
            repo_path = Path(repo_dir)

            # Create the hook configured to apply patches locally, but don't show messages
            hook = SaveApplyPatchHook(apply_patch_locally=True, show_success_message=False)
            # Directly set the output dir (normally set in on_init)
            hook._output_dir = out_path

            # Prepare a fake environment with a LocalRepoConfig pointing to our repo_dir
            env = SimpleNamespace(repo=LocalRepoConfig(path=repo_path))
            hook._env = env
            # Problem statement with an id used to name the patch file
            hook._problem_statement = SimpleNamespace(id="instance-42")

            # Prepare a result object carrying a promising submission
            result = SimpleNamespace(info={"submission": "dummy patch content", "exit_status": "submitted"}, trajectory=None)

            # Replace _apply_patch to capture its arguments instead of actually calling git
            called = {}
            def fake_apply(patch_file: Path, local_dir: Path) -> None:
                called["patch_file"] = Path(patch_file)
                called["local_dir"] = Path(local_dir)
            hook._apply_patch = fake_apply

            # Execute the code under test
            hook.on_instance_completed(result=result)

            # Assertions: _save_patch should have written the patch and our fake _apply_patch should be called
            expected_patch_path = out_path / "instance-42" / "instance-42.patch"
            self.assertTrue(expected_patch_path.exists(), "Expected patch file to be created")
            self.assertIn("patch_file", called, "_apply_patch was not called")
            self.assertEqual(called["patch_file"].resolve(), expected_patch_path.resolve())
            self.assertEqual(called["local_dir"].resolve(), repo_path.resolve())
