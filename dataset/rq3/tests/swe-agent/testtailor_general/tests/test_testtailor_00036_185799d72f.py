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
        """Ensure hooks passed to SWEEnv.__init__ are registered and their on_init is called."""
        # Dynamically locate and import SWEEnv from the sweagent.environment package
        import importlib
        import pkgutil

        env_pkg = importlib.import_module("sweagent.environment")
        SWEEnv = None

        # Direct attribute on package
        if hasattr(env_pkg, "SWEEnv"):
            SWEEnv = getattr(env_pkg, "SWEEnv")

        # Search submodules if not found directly
        if SWEEnv is None and hasattr(env_pkg, "__path__"):
            for finder, name, ispkg in pkgutil.iter_modules(env_pkg.__path__):
                try:
                    mod = importlib.import_module(f"sweagent.environment.{name}")
                except Exception:
                    continue
                if hasattr(mod, "SWEEnv"):
                    SWEEnv = getattr(mod, "SWEEnv")
                    break

        # As a last resort, inspect attributes on the package for a class named SWEEnv
        if SWEEnv is None:
            for attr in dir(env_pkg):
                obj = getattr(env_pkg, attr)
                if isinstance(obj, type) and obj.__name__ == "SWEEnv":
                    SWEEnv = obj
                    break

        if SWEEnv is None:
            raise ImportError("Could not locate SWEEnv in sweagent.environment package")

        # Minimal dummy deployment (no methods are invoked during __init__)
        class DummyDeployment:
            pass

        # Create a simple hook that records whether on_init was called and with which env
        class RecordingHook:
            def __init__(self):
                self.init_called = False
                self.env_received = None

            def on_init(self, *, env):
                self.init_called = True
                self.env_received = env

            # Provide no-op implementations for other optional hook methods to be safe
            def on_copy_repo_started(self, repo): ...
            def on_start_deployment(self): ...
            def on_install_env_started(self): ...
            def on_close(self): ...
            def on_environment_startup(self): ...

        hook = RecordingHook()

        # Construct environment with the hook passed into constructor;
        # this should call add_hook -> hook.on_init(...)
        env = SWEEnv(
            deployment=DummyDeployment(),
            repo=None,
            post_startup_commands=[],
            hooks=[hook],
            name="test-env",
        )

        # Assert the hook's on_init was called and it received the env instance
        self.assertTrue(hook.init_called, "hook.on_init was not called during SWEEnv.__init__")
        self.assertIs(hook.env_received, env, "hook.on_init did not receive the created SWEEnv instance")

        # Assert the hook was added to the combined hooks internal list
        self.assertIn(hook, getattr(env, "_chook")._hooks)
