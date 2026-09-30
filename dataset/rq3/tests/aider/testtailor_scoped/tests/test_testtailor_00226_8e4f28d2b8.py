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
        """When the sounddevice InputStream raises PortAudioError, raw_record_and_transcribe
        should raise a SoundDeviceError with the underlying error message included."""
        # Prepare a fake sounddevice module
        mock_sd = MagicMock()

        # Provide a PortAudioError exception type on the fake module
        class _PortAudioError(Exception):
            pass

        mock_sd.PortAudioError = _PortAudioError

        # query_devices called with no args (in __init__) should return a list of devices,
        # and when called with (device_id, "input") should return a dict containing default_samplerate.
        def _query_devices(*args, **kwargs):
            if len(args) == 0:
                return [{"name": "mock_device", "max_input_channels": 1}]
            return {"default_samplerate": "44100"}

        mock_sd.query_devices.side_effect = _query_devices

        # Define an InputStream context manager that raises PortAudioError on __enter__
        class FakeInputStream:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                raise mock_sd.PortAudioError("simulated access failure")

            def __exit__(self, exc_type, exc, tb):
                return False

        mock_sd.InputStream = FakeInputStream

        # Patch the sounddevice module in sys.modules so the Voice __init__ imports our mock
        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            # Also ensure sf is present so Voice.__init__ does not raise SoundDeviceError
            with patch("aider.voice.sf", MagicMock()):
                voice = Voice()  # should initialize using our mocked sounddevice

                # Call raw_record_and_transcribe and assert the SoundDeviceError is raised
                with self.assertRaises(SoundDeviceError) as cm:
                    voice.raw_record_and_transcribe(history=None, language=None)

                err_msg = str(cm.exception)
                self.assertIn("Error accessing audio input device", err_msg)
                self.assertIn("simulated access failure", err_msg)
