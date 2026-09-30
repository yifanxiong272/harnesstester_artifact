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
        """Ensure that when litellm.transcription raises, raw_record_and_transcribe
        prints the error and returns None (hits the target except branch)."""
        # Fake SoundFile context manager that creates the file so os.path.getsize can run.
        class FakeSoundFile:
            def __init__(self, path, mode=None, samplerate=None, channels=None):
                self.path = path
                self._fh = None

            def __enter__(self):
                # create the file so getsize can succeed
                self._fh = open(self.path, "wb")
                return self

            def write(self, data):
                # simulate writing some bytes for any written data
                if self._fh:
                    self._fh.write(b"\0" * 32)

            def __exit__(self, exc_type, exc, tb):
                if self._fh:
                    self._fh.close()

        # Fake InputStream context manager for sounddevice
        class FakeInputStream:
            def __init__(self, samplerate=None, channels=None, callback=None, device=None):
                self.samplerate = samplerate
                self.channels = channels
                self.callback = callback
                self.device = device

            def __enter__(self):
                # Do nothing; prompt() will be patched to a no-op
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        # Prepare mocked modules/attributes in aider.voice
        with patch("aider.voice.sf", new=MagicMock()) as mock_sf:
            # Replace SoundFile used in the function with our fake implementation
            mock_sf.SoundFile = FakeSoundFile

            # Patch litellm so transcription raises an exception
            with patch("aider.voice.litellm", new=MagicMock()) as mock_litellm:
                mock_litellm.transcription.side_effect = Exception("transcription failed")

                # Patch prompt to be a no-op so the InputStream context exits immediately
                with patch("aider.voice.prompt", new=lambda get_prompt, refresh_interval: None):
                    # Create a fake sounddevice module and put it into sys.modules before Voice imports it
                    fake_sd = MagicMock()
                    # query_devices should return mapping containing default_samplerate
                    fake_sd.query_devices.return_value = {"default_samplerate": 16000}
                    # expose a PortAudioError class attribute to match usage in code
                    fake_sd.PortAudioError = type("PortAudioError", (Exception,), {})
                    # Use our FakeInputStream as the InputStream context manager
                    fake_sd.InputStream = FakeInputStream

                    with patch.dict("sys.modules", {"sounddevice": fake_sd}):
                        # Ensure the aider.voice module uses our patched sf and sounddevice
                        voice = Voice()

                        # Call the target function; because litellm.transcription raises,
                        # the function should catch it, print, and return None.
                        result = voice.raw_record_and_transcribe(history="history text", language="en")
                        self.assertIsNone(result)
