import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.memory.memory')
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
        """When a workspace context RecallAction produces no workspace data, Memory should emit a NullObservation."""

        # Minimal fake EventStream to capture added events
        class FakeEventStream:
            def __init__(self):
                self.subscribers = {}
                self.added = []

            def subscribe(self, subscriber, callback, sid):
                # store subscriber callback for completeness (not used in this test)
                self.subscribers[subscriber] = (callback, sid)

            def add_event(self, event, source):
                # capture the event and the source for assertions
                self.added.append((event, source))

        # Subclass Memory to avoid loading microagents from disk during test
        class TestMemory(Memory):
            def _load_global_microagents(self):
                return None

            def _load_user_microagents(self):
                return None

        ev_stream = FakeEventStream()
        mem = TestMemory(ev_stream, sid='test_sid', status_callback=None)

        # Ensure no repo/knowledge microagents and no repo/runtime/conversation info set
        mem.repo_microagents = {}
        mem.knowledge_microagents = {}
        mem.repository_info = None
        mem.runtime_info = None
        mem.conversation_instructions = None

        # Create RecallAction representing a user-requested workspace context recall
        # RecallAction requires recall_type on initialization
        event = RecallAction(recall_type=RecallType.WORKSPACE_CONTEXT)
        # set internal attributes expected by Event properties
        event._source = EventSource.USER.value  # 'user'
        event._id = 123

        # Trigger handling (synchronous wrapper used by Memory.on_event)
        mem.on_event(event)

        # Validate that exactly one event was added to the event stream
        self.assertEqual(len(ev_stream.added), 1)

        added_event, added_source = ev_stream.added[0]

        # The Memory should have added a NullObservation with empty content and cause set to the original event id
        self.assertIsInstance(added_event, NullObservation)
        self.assertEqual(added_source, EventSource.ENVIRONMENT)
        # content was instantiated as empty string
        self.assertEqual(getattr(added_event, 'content', None), '')
        # the _cause should have been set to the original event id (exposed via .cause property)
        self.assertEqual(added_event.cause, event.id)
