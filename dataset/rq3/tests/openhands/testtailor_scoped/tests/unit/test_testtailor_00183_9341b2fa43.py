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
        """Session.start should return early with a warning when session is closed."""
        # Minimal in-memory FileStore for EventStream to use
        class DummyFileStore:
            def __init__(self):
                self.store = {}

            def write(self, path: str, contents: str | bytes) -> None:
                self.store[path] = contents

            def read(self, path: str) -> str:
                return self.store[path]

            def list(self, path: str) -> list[str]:
                return [k for k in self.store.keys() if k.startswith(path)]

            def delete(self, path: str) -> None:
                if path in self.store:
                    del self.store[path]

        sid = 'test-sid'
        file_store = DummyFileStore()
        # llm_registry and conversation_stats are not used for this early-return path
        llm_registry = object()
        conversation_stats = object()

        session = AgentSession(sid, file_store, llm_registry, conversation_stats)

        # Mark session as closed to trigger the target branch
        session._closed = True

        try:
            # Call start; it should return immediately without raising
            asyncio.run(
                session.start(
                    runtime_name='test-runtime',
                    config=None,
                    agent=None,
                    max_iterations=1,
                )
            )
        finally:
            # Ensure the event stream thread is cleaned up to avoid leaks in tests
            session.event_stream.close()

        # Verify state consistent with early return
        self.assertTrue(session.is_closed())
        self.assertIsNone(session.controller)
        self.assertIsNone(session.runtime)
        self.assertFalse(session._starting)
