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
        """Ensure that when config.actions.open_pr is True, from_config adds an OpenPRHook."""
        tmpdir = __import__("tempfile").TemporaryDirectory()
        try:
            Path = __import__("pathlib", fromlist=["Path"]).Path
            tmp_path = Path(tmpdir.name)

            # Import required classes dynamically to avoid top-level imports
            agents_mod = __import__("sweagent.agent.agents", fromlist=["DefaultAgentConfig"])
            DefaultAgentConfig = agents_mod.DefaultAgentConfig
            models_mod = __import__("sweagent.agent.models", fromlist=["InstantEmptySubmitModelConfig"])
            InstantEmptySubmitModelConfig = models_mod.InstantEmptySubmitModelConfig
            env_mod = __import__("sweagent.environment.swe_env", fromlist=["EnvironmentConfig"])
            EnvironmentConfig = env_mod.EnvironmentConfig
            run_mod = __import__("sweagent.run.run_single", fromlist=["RunSingle", "RunSingleConfig"])
            RunSingle = run_mod.RunSingle
            RunSingleConfig = run_mod.RunSingleConfig
            hooks_open = __import__("sweagent.run.hooks.open_pr", fromlist=["OpenPRConfig", "OpenPRHook"])
            OpenPRConfig = hooks_open.OpenPRConfig
            OpenPRHook = hooks_open.OpenPRHook

            # Build config and enable open_pr
            agent_cfg = DefaultAgentConfig(model=InstantEmptySubmitModelConfig())
            rsc = RunSingleConfig(env=EnvironmentConfig(), agent=agent_cfg, output_dir=tmp_path)
            # Ensure actions object has the desired settings
            rsc.actions.open_pr = True
            rsc.actions.pr_config = OpenPRConfig()

            rs = RunSingle.from_config(rsc)

            # Verify that an OpenPRHook instance was added to the run hooks
            found = any(isinstance(h, OpenPRHook) for h in rs.hooks)
            self.assertTrue(found, "OpenPRHook was not added when config.actions.open_pr is True")
        finally:
            tmpdir.cleanup()
