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
        """When the sounddevice InputStream raises PortAudioError, ensure a SoundDeviceError is raised with the expected message."""
        # Create a fake sounddevice module
        mock_sd = MagicMock()

        # query_devices should behave differently depending on how it's called:
        # - called with no args in Voice.__init__ -> return list of devices
        # - called with (device_id, "input") in raw_record_and_transcribe -> return dict with default_samplerate
        def fake_query_devices(*args, **kwargs):
            if len(args) == 0:
                return [{"name": "test_device", "max_input_channels": 1}]
            return {"default_samplerate": "44100"}

        mock_sd.query_devices = MagicMock(side_effect=fake_query_devices)

        # Define a PortAudioError exception on the mock module
        PortAudioError = type("PortAudioError", (Exception,), {})
        mock_sd.PortAudioError = PortAudioError

        # Make InputStream raise PortAudioError when attempted to be created (simulates audio device access error)
        mock_sd.InputStream = MagicMock(side_effect=mock_sd.PortAudioError("no device access"))

        # Patch the sounddevice module in sys.modules so Voice will import it
        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            # Patch the soundfile dependency used in Voice to avoid initialization errors
            with patch("aider.voice.sf", MagicMock()):
                voice = Voice()  # should initialize using our mocked sounddevice

                # Now call raw_record_and_transcribe and assert the expected SoundDeviceError is raised
                with self.assertRaises(SoundDeviceError) as cm:
                    voice.raw_record_and_transcribe(history=None, language=None)

                msg = str(cm.exception)
                self.assertIn("Error accessing audio input device", msg)
                self.assertIn("no device access", msg)
