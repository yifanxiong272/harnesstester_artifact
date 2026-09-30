import importlib as _testtailor_importlib
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, call, patch

try:
    _testtailor_target = _testtailor_importlib.import_module('aider.voice')
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
        """Ensure get_prompt takes the branch where cnt is set to 0 (pct is NaN or below threshold)."""
        # Create a Voice instance without running __init__ to avoid sounddevice imports
        voice = Voice.__new__(Voice)
        # Force the condition math.isnan(self.pct) to be True
        voice.pct = float("nan")
        # Ensure threshold exists
        voice.threshold = 0.15
        # Set a start_time so duration formatting works
        voice.start_time = time.time() - 1.5

        prompt = voice.get_prompt()

        # Should indicate recording and include seconds text
        self.assertIn("Recording", prompt)
        self.assertIn("sec", prompt)

        # When cnt == 0 the bar is all filled blocks ("█") and contains no "░"
        self.assertIn("█", prompt)
        self.assertNotIn("░", prompt)
