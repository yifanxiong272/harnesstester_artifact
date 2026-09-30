import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.utils.runtime_init')
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
        """Windows branch: should create the given working directory and return None."""
        orig_platform = sys.platform
        initial_cwd = None
        try:
            # Force Windows platform branch
            sys.platform = 'win32'

            # Build a unique directory path under current working directory
            base = os.path.join(os.getcwd(), f'tmp_test_{os.getpid()}_{id(self)}')
            initial_cwd = os.path.join(base, 'some', 'nested', 'dir')

            # Ensure the directory does not exist before call
            if os.path.exists(initial_cwd):
                # Try to remove any pre-existing test dirs to start clean
                try:
                    os.removedirs(initial_cwd)
                except Exception:
                    # If removal fails, choose a different unique base
                    base = os.path.join(os.getcwd(), f'tmp_test_{os.getpid()}_{id(self)}_alt')
                    initial_cwd = os.path.join(base, 'some', 'nested', 'dir')

            self.assertFalse(os.path.exists(initial_cwd))

            # Call the function under test
            result = init_user_and_working_directory('dummyuser', 1001, initial_cwd)

            # On Windows branch, function should return None and create the directory
            self.assertIsNone(result)
            self.assertTrue(os.path.isdir(initial_cwd))
        finally:
            # Cleanup created directories if any and restore original platform
            try:
                if initial_cwd and os.path.exists(initial_cwd):
                    # removedirs will attempt to remove leaf and intermediate empty dirs
                    os.removedirs(initial_cwd)
            except Exception:
                # Best-effort cleanup: remove leaf if still present
                try:
                    if initial_cwd and os.path.isdir(initial_cwd):
                        os.rmdir(initial_cwd)
                except Exception:
                    pass
            sys.platform = orig_platform
