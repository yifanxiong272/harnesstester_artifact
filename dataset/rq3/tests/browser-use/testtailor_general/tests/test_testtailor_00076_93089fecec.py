import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skill_cli.actions')
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
        """Navigate should call BrowserSession._navigate_and_wait with the focused tab id."""
        async def _runner():
            # Prepare a fake BrowserSession (plain mock is fine because we avoid ActionHandler.__init__)
            bs = unittest.mock.Mock()
            bs.agent_focus_target_id = 'focused-tab-123'
            bs._navigate_and_wait = unittest.mock.AsyncMock(return_value=None)

            # Create ActionHandler instance without running __init__ to avoid pydantic validation
            handler = ActionHandler.__new__(ActionHandler)
            handler.bs = bs  # set required attribute directly

            # Call the async navigate method
            test_url = 'https://example.com/test'
            await handler.navigate(test_url)

            # Verify _navigate_and_wait was awaited with the correct arguments
            bs._navigate_and_wait.assert_awaited_once_with(test_url, 'focused-tab-123')

        import asyncio
        asyncio.run(_runner())
