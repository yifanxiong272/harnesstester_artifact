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
        """Ensure get_prompt takes the branch where cnt = 0 (math.isnan(self.pct) True)."""
        # Prepare a fake sounddevice module so Voice.__init__ doesn't raise
        mock_sd = MagicMock()
        mock_sd.query_devices.return_value = [{"name": "test_device", "max_input_channels": 1}]
        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            with patch("aider.voice.sf", MagicMock()):
                voice = Voice()
                # set a valid start_time and a NaN pct to trigger math.isnan branch
                voice.start_time = time.time() - 0.5
                voice.pct = float("nan")

                prompt = voice.get_prompt()
                # The final token in the prompt is the bar
                bar = prompt.split()[-1]

                # When cnt == 0 the implementation produces 10 filled blocks ('█') and no '░'
                self.assertNotIn("░", bar)
                self.assertEqual(bar, "█" * 10)
