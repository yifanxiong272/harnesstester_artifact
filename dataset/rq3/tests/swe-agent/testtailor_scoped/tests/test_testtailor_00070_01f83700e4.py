import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.environment.swe_env')
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
        """Test that SWEEnv.communicate with check='raise' closes the environment and raises on non-zero exit."""

        # Minimal fake deployment/runtime to drive the communicate logic
        class FakeRuntime:
            async def run_in_session(self, action):
                # Return an object with `output` and non-zero `exit_code` to trigger the raise path
                class Obs:
                    def __init__(self):
                        self.output = "some error output"
                        self.exit_code = 1
                return Obs()

        class FakeDeployment:
            def __init__(self):
                self.runtime = FakeRuntime()
                self.stopped = False

            async def stop(self):
                # record that stop was called
                self.stopped = True

        dep = FakeDeployment()
        # Create the environment with minimal required args
        env = SWEEnv(deployment=dep, repo=None, post_startup_commands=[], post_startup_command_timeout=1, name="test-env")

        # Expect RuntimeError because check="raise" and the fake runtime returns exit_code != 0
        with self.assertRaises(RuntimeError) as cm:
            env.communicate("any-command", check="raise", timeout=0.1)

        # ensure close() called which calls deployment.stop()
        self.assertTrue(dep.stopped, "Expected deployment.stop() to be called during close()")

        # ensure the raised message includes the exit code formatting used in the implementation
        self.assertIn("r.exit_code=1", str(cm.exception))
