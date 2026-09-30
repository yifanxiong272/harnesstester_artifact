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
        """communicate should call close() and raise RuntimeError when check='raise' and exit_code != 0"""
        # runtime stub that returns a non-zero exit code
        class RuntimeStub:
            async def run_in_session(self, action):
                class Obs:
                    def __init__(self):
                        self.output = "simulated failure output"
                        self.exit_code = 42
                return Obs()

        # deployment stub with a stop coroutine to detect whether close() was invoked
        class DeploymentStub:
            def __init__(self):
                self.runtime = RuntimeStub()
                self.stopped = False

            async def stop(self):
                self.stopped = True

        deployment = DeploymentStub()
        # create environment with the stub deployment
        env = SWEEnv(deployment=deployment, repo=None, post_startup_commands=[])

        # Expect a RuntimeError and that env.close() was invoked (deployment.stopped becomes True)
        with self.assertRaises(RuntimeError) as cm:
            env.communicate("some-command", check="raise", timeout=1)

        self.assertTrue(deployment.stopped, "Expected deployment.stop() to be called by env.close()")
        msg = str(cm.exception)
        # Verify the message contains the exit code indicator as formatted in the implementation
        self.assertIn("r.exit_code=42", msg)
        self.assertIn("some-command", msg)
