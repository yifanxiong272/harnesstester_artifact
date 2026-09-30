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
        """Ensure docker.from_env() is used and client is exercised; containers matching
        prefix are stopped, exceptions from stop() are swallowed, and client.close() is called.
        """
        # Prepare mock containers
        matching_ok = MagicMock()
        matching_ok.name = "myprefix_container1"
        matching_ok.stop = MagicMock()

        matching_error = MagicMock()
        matching_error.name = "myprefix_container2"
        # stop() will raise APIError which should be caught inside the function
        matching_error.stop.side_effect = docker.errors.APIError("stop failed")

        non_matching = MagicMock()
        non_matching.name = "other_container"
        non_matching.stop = MagicMock()

        mock_containers = [matching_ok, matching_error, non_matching]

        # Prepare mock docker client
        mock_client = MagicMock()
        mock_client.containers.list.return_value = mock_containers
        mock_client.close = MagicMock()

        # Patch docker.from_env to return our mock client
        with patch.object(docker, "from_env", return_value=mock_client) as mock_from_env:
            # Call the function under test; should not raise despite the APIError from one container
            stop_all_containers("myprefix")

            # Assertions: from_env was called, list was queried, appropriate stops attempted, and client closed
            mock_from_env.assert_called_once()
            mock_client.containers.list.assert_called_once_with(all=True)
            matching_ok.stop.assert_called_once()
            matching_error.stop.assert_called_once()
            non_matching.stop.assert_not_called()
            mock_client.close.assert_called_once()
