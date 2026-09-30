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
        """Ensure on_instance_completed returns early when env.repo is not a LocalRepoConfig
        but a patch was saved (i.e., patch_path truthy) so the branch `if not isinstance(self._env.repo, LocalRepoConfig)` is taken.
        """
        # Import needed stdlib modules without top-level import statements
        tempfile = __import__("tempfile")
        types = __import__("types")
        pathlib = __import__("pathlib")
        Path = pathlib.Path

        hook = SaveApplyPatchHook(apply_patch_locally=True, show_success_message=False)

        # Prepare a temporary output dir for the hook
        with tempfile.TemporaryDirectory() as td:
            # Initialize the hook with a run-like object that has output_dir
            run_obj = types.SimpleNamespace(output_dir=Path(td))
            hook.on_init(run=run_obj)

            # Prepare a fake environment whose repo is present but NOT a LocalRepoConfig
            fake_env = types.SimpleNamespace(repo=object())
            # Minimal problem statement with an id
            problem_statement = types.SimpleNamespace(id="inst-42")
            hook.on_instance_start(index=0, env=fake_env, problem_statement=problem_statement)

            # Create a result that contains a submission and a submitted exit_status
            result = types.SimpleNamespace(info={"submission": "diff --git a/foo b/foo\n", "exit_status": "submitted"}, trajectory=None)

            # Call the method under test; it should save the patch and then return early
            ret = hook.on_instance_completed(result=result)

            # Verify the patch file was created and contains the expected content
            expected_patch_file = Path(td) / "inst-42" / "inst-42.patch"
            self.assertIsNone(ret)
            self.assertTrue(expected_patch_file.exists(), f"Expected patch file at {expected_patch_file} to exist")
            contents = expected_patch_file.read_text()
            self.assertIn("diff --git a/foo b/foo", contents)
