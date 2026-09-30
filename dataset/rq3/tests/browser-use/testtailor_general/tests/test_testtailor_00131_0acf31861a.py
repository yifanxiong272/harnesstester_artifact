import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.mcp.__init__')
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
        """Accessing BrowserUseServer triggers lazy import and returns the class."""
        import importlib
        import sys

        # Ensure a fresh import so __getattr__ behavior can be observed
        sys.modules.pop('browser_use.mcp.server', None)
        sys.modules.pop('browser_use.mcp', None)

        m = importlib.import_module('browser_use.mcp')

        # Before attribute access, the server module should not be imported and attribute not in module dict
        self.assertNotIn('browser_use.mcp.server', sys.modules)
        self.assertNotIn('BrowserUseServer', m.__dict__)

        # Access the attribute to trigger __getattr__ branch name == 'BrowserUseServer'
        cls = m.BrowserUseServer

        # After access, the server module should have been imported and the returned object should be the class
        self.assertIn('browser_use.mcp.server', sys.modules)
        from browser_use.mcp.server import BrowserUseServer as Expected
        self.assertIs(cls, Expected)
