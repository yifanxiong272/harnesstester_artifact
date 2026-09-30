import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.controller.state.state_tracker')
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
        """Ensure _init_history returns early and clears history when start_id > end_id + 1."""
        # Minimal in-test file store implementation to satisfy EventStream
        class SimpleMemoryFileStore:
            def __init__(self):
                self.storage = {}

            def write(self, path: str, contents: str | bytes) -> None:
                self.storage[path] = contents

            def read(self, path: str) -> str:
                return self.storage[path]

            def list(self, path: str) -> list[str]:
                # return keys that start with path
                return [k for k in self.storage.keys() if k.startswith(path)]

            def delete(self, path: str) -> None:
                if path in self.storage:
                    del self.storage[path]

        # Setup environment
        mock_file_store = SimpleMemoryFileStore()
        event_stream = EventStream(sid='test-session', file_store=mock_file_store)
        conversation_stats = ConversationStats(None, 'convo-id', None)

        # Create StateTracker and initialize a fresh state
        tracker = StateTracker(sid='test-session', file_store=mock_file_store, user_id=None)
        tracker.set_initial_state(
            id='test-session',
            state=None,
            conversation_stats=conversation_stats,
            max_iterations=1,
            max_budget_per_task=None,
        )

        # Force start_id greater than end_id + 1 to trigger the early-return branch
        tracker.state.start_id = 5
        tracker.state.end_id = 0  # 5 > 0 + 1 holds

        # Pre-populate history to ensure it gets cleared by the early-return
        tracker.state.history = [AgentDelegateAction(agent='a', inputs={})]

        # Call _init_history and verify behavior (should return early and clear history)
        tracker._init_history(event_stream)

        self.assertEqual(tracker.state.history, [])
        # start_id should be unchanged (we returned early before it would be reset)
        self.assertEqual(tracker.state.start_id, 5)
