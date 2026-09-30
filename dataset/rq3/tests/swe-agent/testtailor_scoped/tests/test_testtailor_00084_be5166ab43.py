import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.run.run_single')
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
        """Ensure hooks passed to RunSingle.__init__ are registered via add_hook (on_init called)."""

        class InitRecordingHook(RunHook):
            def __init__(self):
                self.init_called = False

            def on_init(self, *, run):
                # Record that on_init was invoked and that run is a RunSingle instance
                self.init_called = True
                assert isinstance(run, RunSingle)

        hook = InitRecordingHook()

        # Minimal problem statement object with required `id` attribute
        class MinimalPS:
            id = "test-run-single-hook"

            def get_problem_statement(self) -> str:
                return "test"

            def get_extra_fields(self) -> dict:
                return {}

        ps = MinimalPS()

        # Minimal dummy agent and env (types are not enforced at runtime here)
        dummy_agent = object()
        dummy_env = object()

        # Use a directory name (no external imports) as output_dir to avoid relying on tempfile
        out_dir = Path("tmp_run_single_hook_dir")

        # Construct RunSingle with a hooks list to trigger the target branch
        rs = RunSingle(env=dummy_env, agent=dummy_agent, problem_statement=ps, output_dir=out_dir, hooks=[hook])

        # The hook's on_init should have been called during initialization via add_hook
        self.assertTrue(hook.init_called, "Hook.on_init was not called during RunSingle initialization")
