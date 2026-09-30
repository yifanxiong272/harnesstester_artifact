import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.skill_cli.profile_use')
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
        """Simulate install script failing (non-zero returncode) and assert RuntimeError is raised."""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import types

        with tempfile.TemporaryDirectory(prefix='bu-') as d:
            bin_dir = Path(d)
            fake_result = types.SimpleNamespace(returncode=1)

            with patch('browser_use.skill_cli.utils.get_bin_dir', return_value=bin_dir), \
                 patch('shutil.which', return_value='/usr/bin/curl'), \
                 patch('subprocess.run', return_value=fake_result):
                # call the function under test; it should raise RuntimeError on non-zero returncode
                with self.assertRaises(RuntimeError) as ctx:
                    download_profile_use()

                msg = str(ctx.exception)
                self.assertIn('Failed to download profile-use', msg)
                self.assertIn('curl -fsSL https://browser-use.com/profile/cli/install.sh | sh', msg)
