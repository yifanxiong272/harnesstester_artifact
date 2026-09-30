import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.impl.docker.containers')
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
        """Ensure docker.from_env() is invoked and the client is closed when stopping containers."""
        # Prepare a fake docker client whose containers.list(...) returns an empty list
        fake_client = unittest.mock.MagicMock()
        fake_client.containers.list.return_value = []
        fake_client.close = unittest.mock.MagicMock()

        # Patch docker.from_env to return our fake client and call the function under test
        with unittest.mock.patch('docker.from_env', return_value=fake_client) as mock_from_env:
            stop_all_containers('test-prefix')

            # Ensure docker.from_env() was called
            mock_from_env.assert_called_once()

            # Ensure containers.list was called with the expected argument
            fake_client.containers.list.assert_called_once_with(all=True)

            # Ensure the client was closed in the finally block
            fake_client.close.assert_called_once()
