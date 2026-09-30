import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.plugins.vscode.__init__')
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
        """Ensure the plugin disables itself immediately on Windows-like platforms."""
        with patch('os.name', 'nt'):
            plugin = VSCodePlugin()
            # Should return quickly because the code path checks os.name == 'nt'
            asyncio.run(plugin.initialize(username='root'))
            self.assertIsNone(plugin.vscode_port)
            self.assertIsNone(plugin.vscode_connection_token)
