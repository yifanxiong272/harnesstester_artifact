import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('rdagent.app.utils.health_check')
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
        """When docker.from_env raises DockerException, cleanup_container should be called with None."""
        # Determine the module where check_docker_status is defined so we patch the correct attributes
        module = check_docker_status.__module__

        # Make docker.from_env in that module raise a DockerException to exercise the except/finally path
        with patch(f"{module}.docker.from_env", side_effect=docker.errors.DockerException("no docker")):
            # Patch the cleanup_container in the same module so we can assert it was called with None
            with patch(f"{module}.cleanup_container") as mock_cleanup:
                # Call the function under test; it should handle the exception and still call cleanup_container in finally
                check_docker_status()

                # Assert cleanup_container was called once with (None, "health check")
                mock_cleanup.assert_called_once()
                call_args, call_kwargs = mock_cleanup.call_args
                self.assertIsNone(call_args[0])
                self.assertEqual(call_args[1], "health check")
