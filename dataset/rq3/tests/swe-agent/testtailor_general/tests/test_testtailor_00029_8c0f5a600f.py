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
        """Ensure that when a patch is saved but not considered promising, the hook returns
        early (does not attempt to apply the patch) while still saving the patch file.
        """
        # ensure we can access Path and create a temp directory without top-level imports
        Path = __import__("pathlib").Path
        tempfile = __import__("tempfile")
        shutil = __import__("shutil")

        tmpdir = Path(tempfile.mkdtemp())

        # Create the hook configured to attempt applying patches locally
        hook = SaveApplyPatchHook(apply_patch_locally=True, show_success_message=False)

        # Initialize the hook with a fake run object that exposes output_dir
        class Run:
            output_dir = tmpdir

        hook.on_init(run=Run())

        # Prepare a minimal environment and problem statement
        env = type("E", (), {})()
        env.repo = None  # repo doesn't matter for this test since we return earlier

        problem_statement = type("PS", (), {})()
        problem_statement.id = "inst1"

        hook.on_instance_start(index=0, env=env, problem_statement=problem_statement)

        # Create a result object that contains a "submission" (so patch gets saved)
        # but an exit_status that does NOT mark it as promising.
        result = type("R", (), {})()
        result.info = {"submission": "diff --git a/file b/file\n...", "exit_status": "error"}
        result.trajectory = None

        # Replace _apply_patch with a sentinel that would mark if it were called
        hook._apply_patch_called = False

        def fake_apply(patch_file, local_dir):
            hook._apply_patch_called = True

        hook._apply_patch = fake_apply

        # Call the hook; this should save the patch and then return early because
        # _is_promising_patch(info) is False. No exception should be raised.
        returned = hook.on_instance_completed(result=result)

        # The method returns None (early return), and _apply_patch must not have been called.
        self.assertIsNone(returned)
        self.assertFalse(hook._apply_patch_called)

        # The patch file should have been created under the output dir
        patch_file = tmpdir / "inst1" / "inst1.patch"
        self.assertTrue(patch_file.exists())

        # Clean up
        shutil.rmtree(str(tmpdir))
