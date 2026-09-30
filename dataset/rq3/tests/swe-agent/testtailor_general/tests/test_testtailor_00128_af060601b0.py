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
        """Verify that hard_reset calls close (stop) then start on the deployment."""
        calls = []

        class DummyRuntime:
            def __init__(self):
                self.create_session_called = False

            async def create_session(self, req):
                self.create_session_called = True

            async def run_in_session(self, action):
                # emulate a successful command run
                class Result:
                    def __init__(self):
                        self.output = ""
                        self.exit_code = 0
                return Result()

            async def read_file(self, req):
                class R:
                    def __init__(self):
                        self.content = ""
                return R()

            async def write_file(self, req):
                return None

            async def execute(self, cmd):
                return None

        class DummyDeployment:
            def __init__(self):
                self.runtime = DummyRuntime()

            async def start(self):
                calls.append("start")

            async def stop(self):
                calls.append("stop")

        dep = DummyDeployment()
        env = SWEEnv(deployment=dep, repo=None, post_startup_commands=[])
        # Call hard_reset which should call stop then start
        env.hard_reset()

        self.assertEqual(calls, ["stop", "start"])
        self.assertTrue(dep.runtime.create_session_called)
