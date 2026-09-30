import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.session.agent_session')
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
        """Attempting to start a session when controller/runtime already present should raise."""
        # Minimal dummy file store to satisfy EventStream/FileStore usage
        class DummyFileStore:
            def write(self, path: str, contents: str | bytes) -> None:
                return None

            def read(self, path: str) -> str:
                return ""

            def list(self, path: str) -> list[str]:
                return []

            def delete(self, path: str) -> None:
                return None

        sid = "test-sid"
        file_store = DummyFileStore()
        # llm_registry and conversation_stats are not used before the early return,
        # so simple placeholders suffice.
        llm_registry = object()
        conversation_stats = object()

        session = AgentSession(sid, file_store, llm_registry, conversation_stats)

        # Simulate an already-started session by setting controller (could also set runtime)
        session.controller = object()

        # Calling start should immediately raise RuntimeError
        with self.assertRaises(RuntimeError) as cm:
            # Use asyncio.run to execute the coroutine synchronously in the test
            asyncio.run(session.start("runtime-name", None, None, 1))

        self.assertIn(
            "Session already started. You need to close this session and start a new one.",
            str(cm.exception),
        )

        # Cleanup: ensure session is closed to stop background threads started by EventStream
        try:
            asyncio.run(session.close())
        except Exception:
            # Best-effort cleanup; don't fail the test if close has issues
            pass
