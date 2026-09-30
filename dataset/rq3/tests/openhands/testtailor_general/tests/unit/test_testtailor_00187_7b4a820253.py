import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('openhands.events.event_store')
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
        """When should_continue() immediately returns False, search_events should exit
        on the first iteration and yield no events (i.e., return early)."""
        # Create a minimal fake "self" object to pass into the unbound EventStore.search_events.
        class FakeStore:
            # cur_id is only read if end_id is None; set to a positive value for safety.
            cur_id = 5

            # These methods/attributes are not reached because should_continue() will be False,
            # but provide them to avoid AttributeError if implementation changes.
            cache_size = 10

            def _load_cache_page_for_index(self, index):
                raise AssertionError("_load_cache_page_for_index should not be called")

            def get_event(self, id):
                raise AssertionError("get_event should not be called")

        fake = FakeStore()

        # Patch the should_continue function used by search_events to force an early return.
        with patch("openhands.events.event_store.should_continue", return_value=False) as mock_sc:
            # Call the unbound function with our fake instance. Use a range that would
            # normally iterate at least once (start_id=0, end_id=0 -> end_id becomes 1).
            result = list(EventStore.search_events(fake, start_id=0, end_id=0))

            # Because should_continue returned False immediately, no events should be yielded.
            self.assertEqual(result, [])
            mock_sc.assert_called_once()
