import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.app_server.sandbox.sandbox_service')
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
        """When get_sandbox returns None, wait_for_sandbox_running should raise SandboxError."""
        class DummyService(SandboxService):
            async def search_sandboxes(self, page_id: str | None = None, limit: int = 100):
                return []

            async def get_sandbox(self, sandbox_id: str):
                # Simulate sandbox not found
                return None

            async def get_sandbox_by_session_api_key(self, session_api_key: str):
                return None

            async def start_sandbox(self, sandbox_spec_id: str | None = None, sandbox_id: str | None = None):
                # Not used in this test
                return None

            async def resume_sandbox(self, sandbox_id: str):
                return False

            async def pause_sandbox(self, sandbox_id: str):
                return False

            async def delete_sandbox(self, sandbox_id: str):
                return False

        service = DummyService()
        sandbox_id = "missing-sandbox"

        with self.assertRaises(SandboxError) as cm:
            asyncio.run(service.wait_for_sandbox_running(sandbox_id))

        # OpenHandsError may prefix error messages (e.g. "500: ..."), so assert the core text is present
        self.assertIn(f'Sandbox not found: {sandbox_id}', str(cm.exception))
