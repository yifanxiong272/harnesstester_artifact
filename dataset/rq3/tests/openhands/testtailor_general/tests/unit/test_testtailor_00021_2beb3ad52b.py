import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.runtime.builder.docker')
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
        """Constructor should raise AgentRuntimeBuildError for Docker server < 18.09 (non-Podman)."""
        docker_client = MagicMock()
        # Version lower than 18.09 and not Podman
        docker_client.version.return_value = {
            'Version': '17.06.0',
            'Components': [{'Name': 'Engine', 'Version': '17.06.0'}],
        }

        with self.assertRaisesRegex(
            AgentRuntimeBuildError,
            'Docker server version must be >= 18.09 to use BuildKit',
        ):
            DockerRuntimeBuilder(docker_client)
