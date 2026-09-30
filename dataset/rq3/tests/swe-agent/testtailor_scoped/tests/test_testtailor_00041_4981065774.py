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
        """Test that hard_reset calls close (stop) and then start (start + init) on the deployment,
        and that runtime session creation and run_in_session calls happen during start/reset.
        """
        events: list[str] = []

        class DummyResponse:
            def __init__(self, output: str, exit_code: int = 0):
                self.output = output
                self.exit_code = exit_code

        class DummyRuntime:
            async def create_session(self, req):
                # record that session creation happened
                events.append("create_session")

            async def run_in_session(self, action):
                # record the command if available, else a generic marker
                cmd = getattr(action, "command", "<no-cmd>")
                events.append(f"run_in_session:{cmd}")
                return DummyResponse(output=f"OK:{cmd}", exit_code=0)

            async def read_file(self, req):
                return type("R", (), {"content": ""})()

            async def write_file(self, req):
                return None

            async def execute(self, *args, **kwargs):
                events.append("execute")

        class DummyDeployment:
            def __init__(self):
                self.runtime = DummyRuntime()

            async def start(self):
                events.append("start")

            async def stop(self):
                events.append("stop")

        # Create SWEEnv with our dummy deployment. No repo and no post-startup commands.
        dep = DummyDeployment()
        env = SWEEnv(deployment=dep, repo=None, post_startup_commands=[], post_startup_command_timeout=1, hooks=None)

        # Call hard_reset which should call close() -> stop, then start() -> start + create_session + run_in_session calls
        env.hard_reset()

        # Basic assertions about ordering and expected calls
        # stop should happen before start
        self.assertIn("stop", events, "stop was not called on deployment")
        self.assertIn("start", events, "start was not called on deployment")
        self.assertLess(events.index("stop"), events.index("start"), "stop should be called before start in hard_reset")

        # create_session and at least two run_in_session calls should have occurred:
        # - one for setting env variables (export ...)
        # - one for cd /
        self.assertIn("create_session", events, "create_session was not called during start")
        run_calls = [e for e in events if e.startswith("run_in_session:")]
        self.assertGreaterEqual(len(run_calls), 2, f"expected at least 2 run_in_session calls, got: {run_calls}")

        # Ensure one of the run_in_session calls contains LANG/LC_ALL export and one is the 'cd /' call
        self.assertTrue(any("LANG" in e and "LC_ALL" in e for e in run_calls), f"env variable export not seen in run_in_session calls: {run_calls}")
        self.assertTrue(any(e.endswith("cd /") or e.endswith("cd /'") or e.endswith("cd /\"") for e in run_calls), f"'cd /' not seen in run_in_session calls: {run_calls}")
