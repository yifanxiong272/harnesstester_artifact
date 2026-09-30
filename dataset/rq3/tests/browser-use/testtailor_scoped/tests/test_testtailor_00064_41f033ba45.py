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
        """Ensure load_user_config reads command_history.json from CONFIG.BROWSER_USE_CONFIG_DIR."""
        # Use __import__ to avoid relying on top-level import statements in this snippet
        tempfile = __import__('tempfile')
        pathlib = __import__('pathlib')
        json = __import__('json')
        sys = __import__('sys')

        # Prepare a temporary directory and a command_history.json file with known content
        tmp = tempfile.TemporaryDirectory()
        tmp_path = pathlib.Path(tmp.name)
        history_file = tmp_path / 'command_history.json'
        expected_history = ["first_cmd", {"cmd": "second"}]
        with open(history_file, 'w') as f:
            json.dump(expected_history, f)

        # Locate the module where load_user_config is defined
        module = sys.modules[load_user_config.__module__]

        # Save and replace CONFIG.BROWSER_USE_CONFIG_DIR so load_user_config looks in our temp dir
        orig_dir = getattr(module.CONFIG, 'BROWSER_USE_CONFIG_DIR', None)
        module.CONFIG.BROWSER_USE_CONFIG_DIR = tmp_path

        try:
            # Patch get_default_config to return a predictable base config
            with unittest.mock.patch.object(module, 'get_default_config', return_value={'command_history': []}):
                result = module.load_user_config()

            # The returned config should have command_history loaded from our file
            self.assertIn('command_history', result)
            self.assertEqual(result['command_history'], expected_history)
        finally:
            # Restore original CONFIG.BROWSER_USE_CONFIG_DIR and cleanup temp dir
            if orig_dir is None:
                # If it didn't exist originally, remove the attribute we added
                try:
                    delattr(module.CONFIG, 'BROWSER_USE_CONFIG_DIR')
                except Exception:
                    pass
            else:
                module.CONFIG.BROWSER_USE_CONFIG_DIR = orig_dir
            tmp.cleanup()
