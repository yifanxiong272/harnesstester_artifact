import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('pr_agent.git_providers.gerrit_provider')
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
        """Verify _call decodes subprocess stdout and calls subprocess.run with expected kwargs."""
        with unittest.mock.patch('subprocess.run') as mock_run:
            # prepare fake completed process
            fake_result = unittest.mock.Mock()
            fake_result.stdout = b'hello world'
            fake_result.stderr = b''
            mock_run.return_value = fake_result

            # call the function under test
            out = _call('echo', 'hi')

            # assertions
            self.assertEqual(out, 'hello world')
            mock_run.assert_called_once_with(
                ('echo', 'hi'),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
