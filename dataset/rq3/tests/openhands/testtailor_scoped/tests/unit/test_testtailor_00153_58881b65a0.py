import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.impl.local.local_runtime')
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
        """Missing code repo path should raise ValueError containing the installation instructions."""
        # Use a path very unlikely to exist
        bad_path = os.path.join(os.getcwd(), 'definitely_nonexistent_openhands_test_path_42')
        # Ensure the path truly does not exist for the test
        if os.path.exists(bad_path):
            # If by some chance it exists, make a different name
            bad_path = bad_path + '_alt'

        with self.assertRaises(ValueError) as cm:
            check_dependencies(bad_path, check_browser=False)

        msg = str(cm.exception)
        # The error should mention the missing path and include the instructional URL message
        self.assertIn(f'Code repo path {bad_path} does not exist.', msg)
        self.assertIn(
            'Please follow the instructions in https://github.com/OpenHands/OpenHands/blob/main/Development.md to install OpenHands.',
            msg,
        )
