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
        """Test that queued audio blocks are written to the soundfile in raw_record_and_transcribe."""
        # Prepare mocks
        mock_sd = MagicMock()

        # Dummy InputStream context manager that calls the provided callback to enqueue audio
        class DummyInputStream:
            def __init__(self, samplerate=None, channels=None, callback=None, device=None):
                self._callback = callback

            def __enter__(self):
                # simulate two audio blocks
                import numpy as np

                if self._callback:
                    # enqueue two different blocks
                    self._callback(np.ones((10, 1)), None, None, None)
                    self._callback(np.ones((5, 1)) * 2, None, None, None)
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        mock_sd.InputStream = DummyInputStream
        mock_sd.PortAudioError = Exception

        # query_devices is called twice: once in __init__ (no args) and once in raw_record... (with args)
        device_list = [{"name": "mock device", "max_input_channels": 2}]
        mock_sd.query_devices.side_effect = [device_list, {"default_samplerate": "16000"}]

        # Fake SoundFile context manager capturing writes; capture the instance for assertions
        captured_instances = []

        class FakeSoundFile:
            def __init__(self, path, mode="x", samplerate=None, channels=None):
                self.path = path
                self.mode = mode
                self.samplerate = samplerate
                self.channels = channels
                self.writes = []
                captured_instances.append(self)

            def __enter__(self):
                return self

            def write(self, data):
                # record that write was called with the data chunk
                self.writes.append(data)

            def __exit__(self, exc_type, exc, tb):
                return False

        fake_sf_module = MagicMock()
        # Ensure SoundFile returns a new FakeSoundFile instance each time it's called
        def soundfile_factory(path, mode="x", samplerate=None, channels=None):
            return FakeSoundFile(path, mode=mode, samplerate=samplerate, channels=channels)

        fake_sf_module.SoundFile = soundfile_factory

        # Small file size so conversion branch isn't taken
        def fake_getsize(path):
            return 1024

        # Mock transcription to return an object with .text
        fake_transcript = type("T", (), {"text": "transcribed audio"})()
        fake_transcription = MagicMock(return_value=fake_transcript)

        # Mock tempfile.mktemp to return predictable filename
        fake_tempfile_name = "/tmp/fake_recording.wav"

        # Fake open to be used as a context manager returning a file-like object
        class FakeFile:
            def __init__(self):
                self.closed = False

            def read(self, *args, **kwargs):
                return b"audio"

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.closed = True
                return False

        fake_open = MagicMock(side_effect=lambda *a, **k: FakeFile())

        # Patch everything in the aider.voice namespace
        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            with patch("aider.voice.sf", fake_sf_module):
                with patch("aider.voice.tempfile.mktemp", return_value=fake_tempfile_name):
                    with patch("aider.voice.os.path.getsize", fake_getsize):
                        with patch("aider.voice.prompt", lambda *a, **k: None):
                            with patch("aider.voice.open", fake_open):
                                with patch("aider.voice.litellm.transcription", fake_transcription):
                                    # Instantiate and run
                                    voice = Voice()
                                    # Ensure audio_format is wav to avoid conversion path
                                    voice.audio_format = "wav"

                                    # Run the method under test
                                    result = voice.raw_record_and_transcribe(history="history-prompt", language="en")

                                    # Assertions
                                    self.assertEqual(result, "transcribed audio")

                                    # Verify that the fake soundfile had writes recorded (two blocks enqueued)
                                    self.assertEqual(len(captured_instances), 1)
                                    sf_instance = captured_instances[0]
                                    self.assertEqual(len(sf_instance.writes), 2)

                                    # Ensure the queued blocks are array-like and non-empty
                                    first_block = sf_instance.writes[0]
                                    second_block = sf_instance.writes[1]
                                    self.assertTrue(hasattr(first_block, "shape") or hasattr(first_block, "__len__"))
                                    self.assertTrue(hasattr(second_block, "shape") or hasattr(second_block, "__len__"))

                                    # Ensure that fake_open was used to open the file for transcription
                                    fake_open.assert_called_with(fake_tempfile_name, "rb")
