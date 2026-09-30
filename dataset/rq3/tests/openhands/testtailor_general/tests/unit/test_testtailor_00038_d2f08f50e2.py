import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.app_server.sandbox.process_sandbox_service')
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
        """When the first port is already in use, _find_unused_port should try the next port."""
        # Use current directory for working dir to avoid needing tempfile
        service = ProcessSandboxService(
            user_id='test-user',
            sandbox_spec_service=MagicMock(),  # simple mock; not used by _find_unused_port
            base_working_dir='.',
            base_port=9000,
            python_executable='python',
            agent_server_module='openhands.agent_server',
            health_check_path='/alive',
            httpx_client=MagicMock(),
        )

        # First socket instance will raise OSError on bind (simulate port in use)
        s1 = MagicMock()
        s1.__enter__.return_value = s1
        s1.bind.side_effect = OSError()

        # Second socket instance will bind successfully
        s2 = MagicMock()
        s2.__enter__.return_value = s2
        s2.bind.return_value = None

        mock_socket_ctor = MagicMock(side_effect=[s1, s2])

        # Patch the socket.socket used in the module under test
        with patch(
            'openhands.app_server.sandbox.process_sandbox_service.socket.socket',
            mock_socket_ctor,
        ):
            found_port = service._find_unused_port()

        # Since the first port (base_port) raised OSError, the service should return base_port + 1
        self.assertEqual(found_port, service.base_port + 1)
