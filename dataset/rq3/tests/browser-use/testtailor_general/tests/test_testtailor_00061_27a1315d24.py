import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.mcp.controller')
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
        """Register MCP tools should construct wrapper, call connect, and return the wrapper."""
        registry = object()
        mcp_command = 'npx'
        mcp_args = ['@playwright/mcp@latest', '--headless']

        class DummyWrapper:
            def __init__(self, registry_arg, command_arg, args_arg=None):
                self.registry = registry_arg
                self.mcp_command = command_arg
                self.mcp_args = args_arg
                self.connected = False

            async def connect(self):
                # Simulate async connection
                self.connected = True

        # Patch the MCPToolWrapper name in the module where register_mcp_tools is defined
        patch_target = f'{register_mcp_tools.__module__}.MCPToolWrapper'
        with unittest.mock.patch(patch_target) as MockWrapperClass:
            MockWrapperClass.side_effect = lambda *a, **kw: DummyWrapper(*a, **kw)

            # Run the coroutine and get the result
            result = asyncio.run(register_mcp_tools(registry, mcp_command, mcp_args))

            # Validate that the MCPToolWrapper class was constructed with expected args
            MockWrapperClass.assert_called_once()
            called_args = MockWrapperClass.call_args[0]
            self.assertIs(called_args[0], registry)
            self.assertEqual(called_args[1], mcp_command)
            self.assertEqual(called_args[2], mcp_args)

            # Validate the returned wrapper is our DummyWrapper and that connect was awaited
            self.assertIsInstance(result, DummyWrapper)
            self.assertTrue(result.connected)
            self.assertIs(result.registry, registry)
            self.assertEqual(result.mcp_command, mcp_command)
            self.assertEqual(result.mcp_args, mcp_args)
