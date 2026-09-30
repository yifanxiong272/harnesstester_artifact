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
        """Ensure raw_record_and_transcribe initializes the queue and creates a temp wav file path,
        then proceeds to call the transcription and returns the text."""
        # Prepare a real temporary file path that will be returned by tempfile.mktemp
        tmpf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmpf.name
        tmpf.close()
        # Put some bytes so os.path.getsize will work
        with open(tmp_path, "wb") as f:
            f.write(b"\x00\x01\x02")

        # Create a mock sounddevice module with expected behavior
        mock_sd = MagicMock()

        # query_devices should return a device list when called with no args,
        # and a dict containing default_samplerate when called with (device_id, "input")
        def qdevices(*args, **kwargs):
            if len(args) == 0:
                return [{"name": "mock_device", "max_input_channels": 1}]
            else:
                return {"default_samplerate": "16000"}

        mock_sd.query_devices.side_effect = qdevices
        # Provide a simple PortAudioError attribute so exception handling references exist
        mock_sd.PortAudioError = Exception

        # Simple InputStream context manager that does nothing (no actual audio)
        class DummyInputStream:
            def __init__(self, samplerate=None, channels=None, callback=None, device=None):
                self.samplerate = samplerate
                self.channels = channels
                self.callback = callback
                self.device = device

            def __enter__(self):
                # Do not invoke callback; keep queue empty to exercise the target path
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        mock_sd.InputStream = DummyInputStream

        # Patch sys.modules so Voice imports our mock sounddevice
        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            # Patch sf (soundfile) used in the module so file opening doesn't touch FS
            mock_sf = MagicMock()
            # Ensure SoundFile can be used as a context manager
            mock_file_ctx = MagicMock()
            mock_sf.SoundFile.return_value.__enter__.return_value = mock_file_ctx
            with patch("aider.voice.sf", mock_sf):
                # Patch prompt to be a no-op to avoid interactive blocking
                with patch("aider.voice.prompt", lambda *args, **kwargs: None):
                    # Ensure tempfile.mktemp returns our prepared temporary file path
                    with patch("aider.voice.tempfile.mktemp", return_value=tmp_path):
                        # Patch litellm.transcription to return an object with .text
                        class DummyTranscript:
                            def __init__(self, text):
                                self.text = text

                        with patch("aider.voice.litellm") as mock_litellm:
                            mock_litellm.transcription.return_value = DummyTranscript("transcribed text")
                            # Instantiate Voice (will use the mocked sounddevice)
                            with patch("aider.voice.sf", mock_sf):
                                voice = Voice()
                                # Call the method under test
                                result = voice.raw_record_and_transcribe(history="history prompt", language="en")
                                # Assertions: queue was created and transcription returned expected text
                                self.assertIsInstance(voice.q, queue.Queue)
                                self.assertEqual(result, "transcribed text")

        # Cleanup the temporary file if it still exists
        try:
            os.remove(tmp_path)
        except OSError:
            pass
