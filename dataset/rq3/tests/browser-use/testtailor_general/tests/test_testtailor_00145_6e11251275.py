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
        """When a command_history.json exists in CONFIG.BROWSER_USE_CONFIG_DIR it is loaded into the config."""
        # Import modules without top-level imports
        tempfile = __import__('tempfile')
        Path = __import__('pathlib').Path
        json = __import__('json')

        # Ensure CONFIG.load_config is safe and record original to restore later
        orig_load = getattr(CONFIG, 'load_config', None)
        CONFIG.load_config = lambda: {}

        # Ensure expected API key attributes exist so get_default_config doesn't raise
        created_keys = []
        for attr in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY', 'DEEPSEEK_API_KEY', 'GROK_API_KEY'):
            if not hasattr(CONFIG, attr):
                setattr(CONFIG, attr, None)
                created_keys.append(attr)

        # Preserve original BROWSER_USE_CONFIG_DIR to restore later
        orig_dir = getattr(CONFIG, 'BROWSER_USE_CONFIG_DIR', None)

        try:
            # Use TemporaryDirectory to create an isolated config dir
            with tempfile.TemporaryDirectory() as tmpdir:
                CONFIG.BROWSER_USE_CONFIG_DIR = Path(tmpdir)
                history_file = CONFIG.BROWSER_USE_CONFIG_DIR / 'command_history.json'

                # Write a valid JSON command history
                expected_history = ["first command", {"cmd": "second", "data": 2}]
                with open(history_file, "w") as f:
                    json.dump(expected_history, f)

                # Call the function under test
                cfg = load_user_config()

                # Assertions: the command_history key must be present and match the file contents
                self.assertIn('command_history', cfg)
                self.assertEqual(cfg['command_history'], expected_history)
        finally:
            # Restore original CONFIG.load_config
            if orig_load is not None:
                CONFIG.load_config = orig_load
            else:
                if hasattr(CONFIG, 'load_config'):
                    delattr(CONFIG, 'load_config')

            # Restore original BROWSER_USE_CONFIG_DIR
            if orig_dir is not None:
                CONFIG.BROWSER_USE_CONFIG_DIR = orig_dir
            else:
                if hasattr(CONFIG, 'BROWSER_USE_CONFIG_DIR'):
                    delattr(CONFIG, 'BROWSER_USE_CONFIG_DIR')

            # Remove any API key attributes we created
            for attr in created_keys:
                if hasattr(CONFIG, attr):
                    delattr(CONFIG, attr)
