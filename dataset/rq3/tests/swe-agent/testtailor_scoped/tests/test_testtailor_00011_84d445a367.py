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
        """Ensure hooks passed to SWEEnv.__init__ have on_init called and are registered."""
        # Simple hook that records whether on_init was called and captures the env
        class MyHook(EnvHook):
            def __init__(self):
                self.inited = False
                self.env = None

            def on_init(self, *, env):
                self.inited = True
                self.env = env

        hook = MyHook()

        # Minimal dummy deployment object — SWEEnv.__init__ only stores it, doesn't call methods
        class DummyDeployment:
            pass

        deployment = DummyDeployment()

        # Create environment with our hook; this should trigger hook.on_init via add_hook in __init__
        env = SWEEnv(deployment=deployment, repo=None, post_startup_commands=[], hooks=[hook], name="testenv")

        # Assert hook was initialized and received the env instance
        self.assertTrue(hook.inited)
        self.assertIs(hook.env, env)

        # Also assert the hook was registered in the combined hooks container
        self.assertIn(hook, env._chook._hooks)
