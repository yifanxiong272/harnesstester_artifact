import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('sweagent.tools.tools')
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
        """Test that when runtime.execute raises, _is_command_available raises RuntimeError with expected message."""
        # Create a ToolHandler instance without running __init__, since the method doesn't use instance state.
        handler = ToolHandler.__new__(ToolHandler)

        # Prepare mocks: runtime.execute should raise to trigger the except branch.
        runtime_execute = AsyncMock(side_effect=Exception("not found"))
        deployment = MagicMock()
        deployment.runtime.execute = runtime_execute
        env = MagicMock()
        env.deployment = deployment

        # Call the async method and assert it raises the expected RuntimeError.
        with self.assertRaisesRegex(RuntimeError, r"Tool foo is not available in the container\."):
            asyncio.run(handler._is_command_available(env, "foo", {"PATH": "/usr/bin"}))

        # Ensure the runtime execute was awaited exactly once.
        self.assertEqual(runtime_execute.await_count, 1)
