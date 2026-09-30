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
        """Test that when the runtime returns a non-zero exit code and check != 'ignore',
        the environment logs the error messages and returns the output (for 'warn' mode)."""

        # Minimal dummy runtime that returns an observation with non-zero exit_code
        class DummyRuntime:
            async def run_in_session(self, action):
                class R:
                    pass
                r = R()
                r.output = "some error output"
                r.exit_code = 2
                return r

        class DummyDeployment:
            def __init__(self):
                self.runtime = DummyRuntime()

        # Create the environment with the dummy deployment
        env = SWEEnv(deployment=DummyDeployment(), repo=None, post_startup_commands=[])

        # Replace logger with a capturing logger to record error messages
        errors = []

        class CapturingLogger:
            def log(self, *args, **kwargs):
                # ignore trace/info logs for this test
                return

            def error(self, msg):
                errors.append(msg)

            def info(self, *args, **kwargs):
                return

            def debug(self, *args, **kwargs):
                return

        env.logger = CapturingLogger()

        # Call communicate with check='warn' so it should log errors but not raise
        out = env.communicate("mycmd --fail", check="warn")

        # Verify returned output is the runtime output
        self.assertEqual(out, "some error output")

        # Verify that error messages were logged: one with error_msg + output, one with detailed msg including exit code
        assert any("Command failed:\nsome error output" == e for e in errors), f"Expected first error log, got: {errors}"
        assert any("r.exit_code=2" in e for e in errors), f"Expected exit code mention in logs, got: {errors}"
