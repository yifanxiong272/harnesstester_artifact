import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('browser_use.agent.views')
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
        """_update_repetition_stats resets state when recent_action_hashes is empty."""
        detector = ActionLoopDetector(window_size=10)
        # Set prior non-zero state to ensure the method actually resets values
        detector.max_repetition_count = 7
        detector.most_repeated_hash = "some_hash"
        # Ensure recent_action_hashes is empty to hit the early-return branch
        detector.recent_action_hashes = []
        result = detector._update_repetition_stats()
        # Method should return None and reset the repetition tracking fields
        self.assertIsNone(result)
        self.assertEqual(detector.max_repetition_count, 0)
        self.assertIsNone(detector.most_repeated_hash)
