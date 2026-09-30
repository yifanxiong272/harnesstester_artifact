import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skill_cli.commands.browser')
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
        """When there is no active CDP session, _execute_js should raise RuntimeError."""
        # Create a browser_session mock whose get_or_create_cdp_session returns falsy (None)
        bs = Mock()
        bs.get_or_create_cdp_session = AsyncMock(return_value=None)

        # Minimal session-like object with required attribute
        session = type("Obj", (), {})()
        session.browser_session = bs

        # Calling the coroutine should raise the expected RuntimeError
        with self.assertRaises(RuntimeError) as cm:
            asyncio.run(_execute_js(session, "1+1"))

        self.assertEqual(str(cm.exception), "No active browser session")
