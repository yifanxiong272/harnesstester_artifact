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
        """Trigger the branch where check != 'ignore' and r.exit_code != 0 so the error
        logging path in SWEEnv.communicate is executed.
        """
        # Minimal objects to emulate the async runtime behavior expected by SWEEnv.communicate
        class DummyObs:
            def __init__(self, output: str, exit_code: int):
                self.output = output
                self.exit_code = exit_code

        class DummyRuntime:
            async def run_in_session(self, action):
                # Return an observation with a non-zero exit code to trigger the error branch
                return DummyObs("errout", 2)

        class DummyDeployment:
            def __init__(self):
                self.runtime = DummyRuntime()

            async def stop(self):
                # noop for this test
                return None

            async def start(self):
                return None

        # Create environment with the dummy deployment
        env = SWEEnv(deployment=DummyDeployment(), repo=None, post_startup_commands=[])

        # Capture calls to logger.error without importing/mocking frameworks
        calls = []

        def fake_error(*args, **kwargs):
            calls.append((args, kwargs))

        env.logger.error = fake_error

        # Call communicate with check != "ignore" to exercise the logging branch
        out = env.communicate("ls", check="warn")

        # Assertions: output returned and two error logs produced with expected messages
        self.assertEqual(out, "errout")
        self.assertEqual(len(calls), 2)
        # First log: "<error_msg>:\n<output>"
        self.assertEqual(calls[0][0][0], "Command failed:\nerrout")
        # Second log: "Command <repr(input)> failed (r.exit_code=<n>): <error_msg>"
        self.assertEqual(calls[1][0][0], "Command 'ls' failed (r.exit_code=2): Command failed")
