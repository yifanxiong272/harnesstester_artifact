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
        """Ensure start() raises if session already started (controller/runtime set)."""
        # Minimal in-memory FileStore implementation required by EventStream
        class DummyFileStore:
            def __init__(self):
                self.storage = {}

            def write(self, path: str, contents: str | bytes) -> None:
                self.storage[path] = contents

            def read(self, path: str) -> str:
                return self.storage.get(path, '')

            def list(self, path: str) -> list[str]:
                return [k for k in self.storage.keys() if k.startswith(path)]

            def delete(self, path: str) -> None:
                if path in self.storage:
                    del self.storage[path]

        sid = 'test-session-xx'
        file_store = DummyFileStore()
        # llm_registry and conversation_stats are not used for this early check, pass simple dummies
        llm_registry = object()
        conversation_stats = object()

        session = AgentSession(sid, file_store, llm_registry, conversation_stats)
        try:
            # Simulate an already-started session by setting controller to a truthy value
            session.controller = object()

            with self.assertRaises(RuntimeError) as cm:
                # Call start asynchronously; arguments besides the check can be simple dummies
                asyncio.run(
                    session.start(
                        runtime_name='dummy-runtime',
                        config=object(),
                        agent=object(),
                        max_iterations=1,
                    )
                )

            self.assertIn('Session already started', str(cm.exception))
        finally:
            # Ensure event stream thread is cleaned up to avoid side effects on other tests
            try:
                session.event_stream.close()
            except Exception:
                pass
