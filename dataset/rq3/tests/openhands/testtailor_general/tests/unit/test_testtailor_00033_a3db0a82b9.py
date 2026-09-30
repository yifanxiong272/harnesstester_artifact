import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.utils.git_changes')
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
        """Verify subprocess.run is used and byte selection + error handling behave correctly."""
        # Helper dummy result to mimic subprocess.CompletedProcess-like object
        class DummyResult:
            def __init__(self, stdout: bytes, stderr: bytes, returncode: int):
                self.stdout = stdout
                self.stderr = stderr
                self.returncode = returncode

        # Scenario 1: returncode == 0 and stderr is present -> should return decoded stderr.strip()
        with unittest.mock.patch('subprocess.run') as mock_run:
            mock_run.return_value = DummyResult(stdout=b'ok\n', stderr=b'err_msg\n', returncode=0)
            # call the function under test; assume `run` is available in the test globals
            result = run('some-cmd', cwd='/some/dir')
            self.assertEqual(result, 'err_msg')

            # ensure subprocess.run was invoked with the expected kwargs at least once
            mock_run.assert_called()
            called_kwargs = mock_run.call_args[1]
            self.assertTrue(called_kwargs.get('shell') is True)
            self.assertIn('stdout', called_kwargs)
            self.assertIn('stderr', called_kwargs)
            self.assertEqual(called_kwargs.get('cwd'), '/some/dir')

        # Scenario 2: non-zero returncode -> should raise RuntimeError and include decoded byte content
        with unittest.mock.patch('subprocess.run') as mock_run:
            # stderr empty so byte_content will pick stdout
            mock_run.return_value = DummyResult(stdout=b'failure output\n', stderr=b'', returncode=2)
            with self.assertRaisesRegex(RuntimeError, r'error_running_cmd:2:failure output'):
                run('failing-cmd', cwd='.')
