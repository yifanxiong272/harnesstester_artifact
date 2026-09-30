import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skill_cli.commands.setup')
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
        """Exercise _prompt when yes is False: normal replies and exception branch."""
        # 'y' should be treated as confirmation
        with unittest.mock.patch('builtins.input', return_value='y'):
            self.assertTrue(_prompt('Proceed?', yes=False))

        # empty reply (default) should be treated as confirmation
        with unittest.mock.patch('builtins.input', return_value=''):
            self.assertTrue(_prompt('Proceed?', yes=False))

        # explicit 'n' should be treated as non-confirmation
        with unittest.mock.patch('builtins.input', return_value='n'):
            self.assertFalse(_prompt('Proceed?', yes=False))

        # input raising EOFError should hit the except branch and return False
        with unittest.mock.patch('builtins.input', side_effect=EOFError):
            self.assertFalse(_prompt('Proceed?', yes=False))
