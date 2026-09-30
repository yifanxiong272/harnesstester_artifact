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
        """When a command_history.json file exists but contains invalid JSON,
        load_user_config should catch JSONDecodeError and set command_history to [].
        """
        # create a unique temporary directory under cwd (avoid relying on tempfile import)
        tmp_path = Path.cwd() / f"tmp_test_cmd_history_{id(self)}"
        tmp_path.mkdir(parents=True, exist_ok=True)

        # backup original config dir and replace it
        orig_dir = CONFIG.BROWSER_USE_CONFIG_DIR
        CONFIG.BROWSER_USE_CONFIG_DIR = tmp_path

        # create an invalid JSON file so json.load raises JSONDecodeError
        history_file = tmp_path / 'command_history.json'
        history_file.write_text("not a valid json")

        # Patch get_default_config used by load_user_config to return a known starting dict
        orig_get_default = load_user_config.__globals__.get('get_default_config')
        load_user_config.__globals__['get_default_config'] = lambda: {'command_history': ['existing']}

        try:
            cfg = load_user_config()
            # Ensure the function returned a dict and that the invalid JSON resulted in empty command_history
            self.assertIsInstance(cfg, dict)
            self.assertIn('command_history', cfg)
            self.assertEqual(cfg['command_history'], [])
        finally:
            # restore patched global and CONFIG attribute
            if orig_get_default is None:
                del load_user_config.__globals__['get_default_config']
            else:
                load_user_config.__globals__['get_default_config'] = orig_get_default
            CONFIG.BROWSER_USE_CONFIG_DIR = orig_dir

            # cleanup created files and directory
            try:
                if history_file.exists():
                    history_file.unlink()
                if tmp_path.exists():
                    tmp_path.rmdir()
            except Exception:
                # best-effort cleanup; ignore errors here
                pass
