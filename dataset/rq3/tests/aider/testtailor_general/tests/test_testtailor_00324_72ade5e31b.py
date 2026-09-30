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
        """Verify queued audio blocks are written to the SoundFile in raw_record_and_transcribe."""
        # Prepare a temporary file path to be returned by tempfile.mktemp inside the method
        tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        tmp_path = tmpf.name
        tmpf.write(b"\x00\x01")  # ensure file exists for open(...)
        tmpf.close()

        # Mock sounddevice with InputStream that calls the provided callback to enqueue audio blocks
        mock_sd = MagicMock()

        def query_devices_side_effect(*args, **kwargs):
            # When called without args, return a list of devices (used in __init__)
            if len(args) == 0:
                return [{"name": "mock_device", "max_input_channels": 1}]
            # When called with (device_id, "input"), return a dict with default_samplerate
            return {"default_samplerate": "44100"}

        mock_sd.query_devices.side_effect = query_devices_side_effect
        mock_sd.PortAudioError = Exception

        import numpy as _np

        class DummyInputStream:
            def __init__(self, samplerate, channels, callback, device):
                self._callback = callback

            def __enter__(self):
                # simulate two audio blocks being delivered during recording
                block1 = _np.ones((1024, 1), dtype=_np.float32)
                block2 = 0.5 * _np.ones((1024, 1), dtype=_np.float32)
                # Callback signature: (indata, frames, time, status)
                self._callback(block1, None, None, None)
                self._callback(block2, None, None, None)
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        mock_sd.InputStream = DummyInputStream

        # Mock sf.SoundFile to provide a context manager whose write() we can inspect
        mock_sf = MagicMock()
        enter_obj = MagicMock()
        mock_sf.SoundFile.return_value.__enter__.return_value = enter_obj

        # Mock litellm.transcription to return an object with .text
        mock_transcript = MagicMock()
        mock_transcript.text = "transcribed audio"
        # We'll patch the transcription function to return that object
        # Also patch prompt to be a no-op so recording loop completes
        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            with patch("aider.voice.sf", new=mock_sf):
                with patch("aider.voice.prompt", new=MagicMock()):
                    with patch("aider.voice.tempfile.mktemp", return_value=tmp_path):
                        with patch("aider.voice.os.path.getsize", return_value=100):
                            with patch("aider.voice.litellm.transcription", return_value=mock_transcript):
                                # Instantiate Voice (will pick up our mocked sounddevice and sf)
                                voice = Voice()
                                # Call the method under test
                                result = voice.raw_record_and_transcribe(history="history", language="en")
                                # Ensure transcription result is propagated
                                self.assertEqual(result, "transcribed audio")
                                # Ensure SoundFile.write was called for each enqueued block (2 calls)
                                self.assertEqual(enter_obj.write.call_count, 2)

        # Cleanup the temp file we created
        try:
            os.remove(tmp_path)
        except Exception:
            pass
