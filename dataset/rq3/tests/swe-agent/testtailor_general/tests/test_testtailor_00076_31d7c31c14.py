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
        """Ensure that when a promising patch is saved but env.repo is None,
        the hook returns early (does not try to apply the patch)."""
        from types import SimpleNamespace
        from pathlib import Path
        import tempfile

        # Create hook that would attempt to apply patches locally
        hook = SaveApplyPatchHook(apply_patch_locally=True, show_success_message=False)

        # Prepare a temporary output dir and initialize the hook
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            hook.on_init(run=SimpleNamespace(output_dir=out_dir))

            # Prepare env with repo = None (this is the branch we want to hit)
            env = SimpleNamespace(repo=None)
            problem_statement = SimpleNamespace(id="instance-42")

            # Start the instance so hook stores env and problem statement
            hook.on_instance_start(index=0, env=env, problem_statement=problem_statement)

            # Prepare a result that has a promising submission
            submission_text = "diff --git a/file b/file\n--- a/file\n+++ b/file\n@@ -1 +1 @@\n-old\n+new\n"
            result = SimpleNamespace(info={"submission": submission_text, "exit_status": "submitted"}, trajectory=None)

            # Ensure _apply_patch is not called (would raise if invoked)
            def _apply_patch_should_not_be_called(*args, **kwargs):
                raise AssertionError("apply_patch should not be called when env.repo is None")
            hook._apply_patch = _apply_patch_should_not_be_called

            # Execute the hook; should save the patch and then return early without applying
            hook.on_instance_completed(result=result)

            # Verify the patch file was created and contains the submission
            patch_path = out_dir / problem_statement.id / f"{problem_statement.id}.patch"
            self.assertTrue(patch_path.exists(), "Patch file was not saved")
            content = patch_path.read_text()
            self.assertEqual(content, submission_text)
