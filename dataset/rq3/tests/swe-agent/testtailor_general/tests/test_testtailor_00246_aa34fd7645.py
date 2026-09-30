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
        """Ensure hooks passed into RunSingle.__init__ are added and their on_init is called."""
        # Minimal problem statement stub with required `id`
        class SimpleProblemStatement:
            def __init__(self, id: str):
                self.id = id

            def get_problem_statement(self) -> str:
                return "ps"

            def get_extra_fields(self) -> dict:
                return {}

        # Recording hook to verify on_init(run=...) is called
        class RecordingHook(RunHook):
            def __init__(self):
                self.recorded_run = None
                self.on_init_called = False

            def on_init(self, *, run):
                self.on_init_called = True
                self.recorded_run = run

        # Create stubs for env and agent (only stored, not used during init)
        env_stub = object()
        agent_stub = object()
        ps = SimpleProblemStatement(id="test_hook_instance")

        hook = RecordingHook()
        # Construct RunSingle with the hook list to exercise `for hook in hooks or []: self.add_hook(hook)`
        rs = RunSingle(env=env_stub, agent=agent_stub, problem_statement=ps, hooks=[hook])

        # After initialization the hook's on_init should have been called and the run passed
        self.assertTrue(hook.on_init_called, "Hook.on_init was not called during RunSingle.__init__")
        self.assertIs(hook.recorded_run, rs, "Hook.on_init received incorrect run instance")
        # And the RunSingle.hooks property should include the hook
        self.assertIn(hook, rs.hooks)
