import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.impl.cli.cli_runtime')
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
        """When config.workspace_base is provided, CLIRuntime should use it as the workspace path
        and set config.workspace_mount_path_in_sandbox accordingly."""
        import tempfile
        import os
        import shutil
        import openhands.runtime as runtime_mod

        # Patch Runtime.__init__ to avoid running base initializer (we'll inject config manually).
        original_runtime_init = runtime_mod.Runtime.__init__
        runtime_mod.Runtime.__init__ = lambda self, *a, **k: None

        # Create a temporary directory to act as the provided workspace_base
        temp_ws = tempfile.mkdtemp(prefix='test_openhands_ws_')

        # Create a minimal fake config object with the attributes expected by CLIRuntime.__init__
        class FakeConfig:
            def __init__(self, workspace_base):
                self.workspace_base = workspace_base
                # This should be set by CLIRuntime.__init__
                self.workspace_mount_path_in_sandbox = None

                # Minimal attributes referenced elsewhere to avoid attribute errors
                class DummySandbox:
                    timeout = 1

                self.sandbox = DummySandbox()

                class DummyMCP:
                    sse_servers = []
                    shttp_servers = []
                    stdio_servers = []

                self.mcp = DummyMCP()
                self.default_agent = None

            def get_llm_config_from_agent(self, _):
                return None

            def get_agent_to_llm_config_map(self):
                return {}

        fake_config = FakeConfig(workspace_base=temp_ws)

        try:
            # Create an uninitialized CLIRuntime instance
            rt_instance = runtime_mod.CLIRuntime.__new__(runtime_mod.CLIRuntime)

            # Ensure the instance has the config attribute that CLIRuntime.__init__ expects
            rt_instance.config = fake_config

            # Call the CLIRuntime.__init__ (super init is patched to no-op)
            runtime_mod.CLIRuntime.__init__(
                rt_instance,
                fake_config,
                event_stream=None,
                llm_registry=None,
                sid='testsid',
                plugins=None,
                env_vars=None,
                status_callback=None,
                attach_to_existing=False,
                headless_mode=False,
                user_id=None,
                git_provider_tokens=None,
            )

            # Assertions: workspace path should be set to the provided workspace_base
            self.assertEqual(rt_instance._workspace_path, temp_ws)
            # The config value should have been updated as well
            self.assertEqual(fake_config.workspace_mount_path_in_sandbox, temp_ws)
            # The file_editor should have been set up
            self.assertTrue(hasattr(rt_instance, 'file_editor'))
            # Runtime should be initialized flag still False until connect() is called
            self.assertFalse(getattr(rt_instance, '_runtime_initialized', True))
        finally:
            # Restore patched attributes
            runtime_mod.Runtime.__init__ = original_runtime_init
            # Cleanup temporary workspace
            try:
                shutil.rmtree(temp_ws)
            except Exception:
                pass
