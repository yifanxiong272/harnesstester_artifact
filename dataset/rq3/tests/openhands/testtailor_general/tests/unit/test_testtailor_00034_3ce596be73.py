import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.routes.manage_conversations')
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
        """Ensure conversations without created_at are skipped by the age filter."""
        # Object that lacks 'created_at' attribute and should be skipped
        class NoCreated:
            def __init__(self):
                self.conversation_id = "no_created"

        # Simple object that has a created_at attribute and should be kept
        class WithCreated:
            def __init__(self, created_at):
                self.conversation_id = "with_created"
                self.created_at = created_at

        no_created = NoCreated()
        recent = WithCreated(datetime.now(timezone.utc))

        # Call the function under test with a large max_age_seconds so recent stays
        results = _filter_conversations_by_age([no_created, recent], max_age_seconds=3600)

        # Only the conversation with a created_at attribute should be returned
        self.assertEqual(len(results), 1)
        self.assertIs(results[0], recent)
