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
        """Ensure missing home directory is created by setup.handle via patched get_home_dir."""
        # Import needed modules via __import__ to avoid top-level imports
        tempfile = __import__('tempfile')
        pathlib = __import__('pathlib')
        Path = pathlib.Path
        os = __import__('os')
        shutil = __import__('shutil')

        # Import the setup module under test
        commands_mod = __import__('browser_use.skill_cli.commands', fromlist=['setup'])
        setup_mod = getattr(commands_mod, 'setup')

        # Prepare a non-existent home directory under a temporary parent
        with tempfile.TemporaryDirectory(prefix='bu-') as parent:
            home = Path(parent) / 'new_home_dir'
            # Ensure it does not exist before running handle
            if home.exists():
                if home.is_dir():
                    shutil.rmtree(home)
                else:
                    home.unlink()

            # Patch utils.get_home_dir so handle() returns our intended (non-existent) path
            utils_mod = __import__('browser_use.skill_cli.utils', fromlist=['get_home_dir'])
            setattr(utils_mod, 'get_home_dir', lambda: home)

            # Short-circuit external installs/checks so test runs quickly and deterministically
            setup_mod._check_chromium = lambda: True
            setup_mod._install_chromium = lambda: True
            setup_mod._install_profile_use = lambda: True
            setup_mod._install_cloudflared = lambda: True
            setup_mod._prompt = lambda message, yes: True

            # Patch profile_use.get_profile_use_binary to return True to avoid install flow
            pu_mod = __import__('browser_use.skill_cli.profile_use', fromlist=['get_profile_use_binary'])
            setattr(pu_mod, 'get_profile_use_binary', lambda: True)

            # Patch config module display to a minimal safe structure
            cfg_mod = __import__('browser_use.skill_cli.config', fromlist=['get_config_display', 'CLI_DOCS_URL'])
            setattr(cfg_mod, 'get_config_display', lambda: [])
            setattr(cfg_mod, 'CLI_DOCS_URL', 'http://example')

            # Ensure any existing env var does not interfere
            prev_env = os.environ.pop('BROWSER_USE_HOME', None) if 'BROWSER_USE_HOME' in os.environ else None

            try:
                # Run the setup; this should cause the code path that creates the home directory
                result = setup_mod.handle(yes=True)
            finally:
                # Restore environment
                if prev_env is not None:
                    os.environ['BROWSER_USE_HOME'] = prev_env

            # Assertions: home directory should have been created and result should record it as ok
            self.assertTrue(home.exists(), "Expected home directory to be created by setup.handle()")
            self.assertIn('home_dir', result)
            self.assertEqual(result['home_dir'], 'ok')
