import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.cli')
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
        """Ensure save_user_config trims history longer than MAX_HISTORY_LENGTH and writes file."""
        # Import needed modules dynamically to avoid top-level import statements
        tempfile = __import__('tempfile')
        pathlib = __import__('pathlib')
        json = __import__('json')

        orig_dir = CONFIG.BROWSER_USE_CONFIG_DIR
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Point CONFIG to a temporary directory
                CONFIG.BROWSER_USE_CONFIG_DIR = pathlib.Path(tmpdir)

                # Create a command history longer than MAX_HISTORY_LENGTH to force trimming
                total_entries = MAX_HISTORY_LENGTH + 5
                history = [f"cmd_{i}" for i in range(total_entries)]
                config = {'command_history': history}

                # Call the function under test
                save_user_config(config)

                # Verify the history file was created and contains only the last MAX_HISTORY_LENGTH entries
                history_file = CONFIG.BROWSER_USE_CONFIG_DIR / 'command_history.json'
                self.assertTrue(history_file.exists(), "History file was not created")

                with open(history_file, 'r', encoding='utf-8') as f:
                    saved_history = json.load(f)

                expected = history[-MAX_HISTORY_LENGTH:]
                self.assertEqual(saved_history, expected)
            finally:
                # Restore original CONFIG
                CONFIG.BROWSER_USE_CONFIG_DIR = orig_dir
