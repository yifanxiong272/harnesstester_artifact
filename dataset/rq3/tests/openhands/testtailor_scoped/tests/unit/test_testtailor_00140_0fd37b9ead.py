import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.server.services.conversation_stats')
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
    def test_case_XX(self):
        """Ensure merge_and_save drops zero-cost restored metrics from both sides before merging."""
        # Dynamically import needed classes/modules to avoid relying on external imports at top-level
        InMemoryFileStore = __import__('openhands.storage.memory', fromlist=['InMemoryFileStore']).InMemoryFileStore
        ConversationStats = __import__('openhands.server.services.conversation_stats', fromlist=['ConversationStats']).ConversationStats
        Metrics = __import__('openhands.llm.metrics', fromlist=['Metrics']).Metrics
        base64 = __import__('base64')
        pickle = __import__('pickle')

        # Setup an in-memory file store and two ConversationStats instances
        fs = InMemoryFileStore({})
        stats_a = ConversationStats(file_store=fs, conversation_id='convA', user_id='user-A')
        stats_b = ConversationStats(file_store=fs, conversation_id='convB', user_id='user-B')

        # Create restored metrics: some with non-zero cost (should be kept), some zero (should be dropped)
        keep_a = Metrics(model_name='m-keep-a')
        keep_a.add_cost(0.05)
        zero_a = Metrics(model_name='m-zero-a')  # accumulated_cost == 0

        keep_b = Metrics(model_name='m-keep-b')
        keep_b.add_cost(0.10)
        zero_b = Metrics(model_name='m-zero-b')  # accumulated_cost == 0

        stats_a.restored_metrics = {'keep-a': keep_a, 'zero-a': zero_a}
        stats_b.restored_metrics = {'keep-b': keep_b, 'zero-b': zero_b}

        # Sanity checks before merge
        self.assertIn('zero-a', stats_a.restored_metrics)
        self.assertIn('zero-b', stats_b.restored_metrics)

        # Perform merge_and_save which should drop zero-cost restored entries on both sides and then merge
        stats_a.merge_and_save(stats_b)

        # After merge: zero-cost entries must be removed, non-zero entries must be present
        self.assertIn('keep-a', stats_a.restored_metrics)
        self.assertIn('keep-b', stats_a.restored_metrics)
        self.assertNotIn('zero-a', stats_a.restored_metrics)
        self.assertNotIn('zero-b', stats_a.restored_metrics)

        # Verify persisted data (save_metrics combines restored and service_to_metrics)
        encoded = fs.read(stats_a.metrics_path)
        pickled = base64.b64decode(encoded)
        persisted = pickle.loads(pickled)

        self.assertIn('keep-a', persisted)
        self.assertIn('keep-b', persisted)
        self.assertNotIn('zero-a', persisted)
        self.assertNotIn('zero-b', persisted)
